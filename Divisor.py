import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from tkinterdnd2 import DND_FILES, TkinterDnD
import warnings
import ollama

# Silencia avisos de substituição de fonte
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- CLASSE DO PDF ---
class PDF_Customizavel(FPDF):
    def __init__(self, titulo_topo, texto_rodape, fonte_escolhida):
        super().__init__()
        self.titulo_topo = titulo_topo
        self.texto_rodape = texto_rodape
        self.fonte_pdf = "helvetica" if fonte_escolhida.lower() == "arial" else fonte_escolhida
        
        if self.fonte_pdf.lower() not in ["helvetica", "courier", "times"]:
            try:
                caminho_fontes = "C:\\Windows\\Fonts\\"
                self.add_font(self.fonte_pdf, "", caminho_fontes + self.fonte_pdf.lower() + ".ttf")
                self.add_font(self.fonte_pdf, "B", caminho_fontes + self.fonte_pdf.lower() + "bd.ttf")
            except:
                self.fonte_pdf = "helvetica"

    def header(self):
        self.set_font(self.fonte_pdf, "I", 8)
        self.cell(0, 10, self.titulo_topo, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.fonte_pdf, "I", 8)
        self.cell(0, 10, f"{self.texto_rodape} - Página {self.page_no()}", align="C")

# --- FUNÇÕES DE SUPORTE ---
def limpar_texto_para_pdf(texto):
    subs = {"—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "\u2022": "-", "\u2014": "-"}
    for k, v in subs.items(): texto = texto.replace(k, v)
    return texto.encode('latin-1', 'replace').decode('latin-1')

def alternar_tema():
    mode = "light" if switch_tema.get() == 1 else "dark"
    ctk.set_appearance_mode(mode)
    bg_color = ctk.ThemeManager.theme["CTk"]["fg_color"]
    janela.configure(bg=bg_color[1] if mode == "dark" else bg_color[0])

def obter_caminho_drop(event):
    path = event.data.strip('{}')
    entry_caminho.configure(state="normal")
    entry_caminho.delete(0, ctk.END)
    entry_caminho.insert(0, path)
    entry_caminho.configure(state="readonly")

# --- LÓGICA DE PROCESSAMENTO ---
def iniciar_processamento():
    caminho_txt = entry_caminho.get()
    nome_pdf = entry_nome_arquivo.get().strip()
    
    if not caminho_txt or not os.path.exists(caminho_txt):
        messagebox.showwarning("Erro", "Selecione um arquivo .txt!")
        return
    if not nome_pdf:
        messagebox.showwarning("Erro", "Defina o nome do arquivo!")
        return

    pasta_destino = filedialog.askdirectory(title="Onde guardar o PDF?")
    if not pasta_destino: return

    try:
        label_status.configure(text="Status: Lendo arquivo...", text_color="#3B8ED0")
        janela.update()

        with open(caminho_txt, "r", encoding="utf-8") as f:
            texto = f.read()

        # Ajuste de tamanho para evitar alucinações da IA
        TAMANHO_MAXIMO = 5000 
        inicio, partes = 0, []
        while inicio < len(texto):
            fim = min(inicio + TAMANHO_MAXIMO, len(texto))
            if fim < len(texto):
                ponto = texto.rfind('.', inicio, fim)
                fim = ponto + 1 if ponto != -1 and ponto > inicio else fim
            partes.append(texto[inicio:fim].strip())
            inicio = fim

        pdf = PDF_Customizavel(entry_topo.get(), entry_rodape.get(), combo_fonte.get())
        pdf.set_left_margin(20)
        pdf.set_right_margin(20)
        pdf.add_page()

        total = len(partes)
        for i, conteudo in enumerate(partes):
            if switch_ia.get() == 1:
                label_status.configure(text=f"IA Corrigindo Parte {i+1} de {total}...", text_color="#A29BFE")
                janela.update()
                
                try:
                    # PROMPT REESTRUTURADO PARA SAÍDA CRUA
                    response = ollama.chat(model='llama3', messages=[
                        {
                            'role': 'system', 
                            'content': (
                                "Você é um motor de correção ortográfica e gramatical. "
                                "Sua tarefa é APENAS corrigir a pontuação e erros de escrita. "
                                "REGRAS CRÍTICAS: "
                                "1. Não responda com introduções (ex: 'Aqui está'). "
                                "2. Não forneça análises ou explicações. "
                                "3. Não altere o estilo ou vocabulário. "
                                "4. Retorne APENAS o texto corrigido, nada mais."
                            )
                        },
                        {'role': 'user', 'content': f"Corrija este texto agora:\n\n{conteudo}"}
                    ])
                    conteudo = response['message']['content'].strip()
                except Exception as e:
                    messagebox.showerror("Erro IA", "Ollamas fora do ar ou erro no modelo.")
                    return

            # Escrita no PDF
            pdf.set_font(pdf.fonte_pdf, "B", 16)
            pdf.cell(0, 15, f"Parte {i+1}", align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 170, pdf.get_y())
            pdf.ln(5)
            pdf.set_font(pdf.fonte_pdf, size=11)
            
            # Garantir que o texto da IA não venha com aspas extras no início/fim
            conteudo_limpo = conteudo.strip('"').strip("'")
            
            pdf.multi_cell(0, 7, text=limpar_texto_para_pdf(conteudo_limpo), align="J")
            pdf.ln(10)
            
            val = (i + 1) / total
            progress_bar.set(val)
            label_status.configure(text=f"Progresso: {int(val*100)}%", text_color="#3B8ED0")
            janela.update()

        if not nome_pdf.lower().endswith(".pdf"): nome_pdf += ".pdf"
        pdf.output(os.path.join(pasta_destino, nome_pdf))

        label_status.configure(text="Status: Concluído!", text_color="#2ECC71")
        messagebox.showinfo("Sucesso", "PDF Gerado com Correção Direta da IA!")

    except Exception as e:
        label_status.configure(text="Status: Erro.", text_color="#E74C3C")
        messagebox.showerror("Erro", str(e))

# --- INTERFACE (IGUAL ANTERIOR COM PEQUENO AJUSTE DE ALTURA) ---
janela = TkinterDnD.Tk()
ctk.set_appearance_mode("dark")
janela.title("PDF Master Pro v4.6 - Clean AI")
janela.geometry("550x920")

bg_color = ctk.ThemeManager.theme["CTk"]["fg_color"]
janela.configure(bg=bg_color[1]) 

frame_top = ctk.CTkFrame(janela, fg_color="transparent")
frame_top.pack(pady=10, padx=20, fill="x")

switch_ia = ctk.CTkSwitch(frame_top, text="Correção Direta IA (Llama 3)", progress_color="#A29BFE")
switch_ia.pack(side="left")

switch_tema = ctk.CTkSwitch(frame_top, text="Modo Claro", command=alternar_tema)
switch_tema.pack(side="right")

lbl_titulo_main = ctk.CTkLabel(janela, text="EDITOR DE LIVROS PDF", font=("Roboto", 24, "bold"))
lbl_titulo_main.pack(pady=10)

frame_drop = ctk.CTkFrame(janela, border_width=2, border_color="#3B8ED0")
frame_drop.pack(pady=10, padx=40, fill="x")
frame_drop.drop_target_register(DND_FILES)
frame_drop.dnd_bind('<<Drop>>', obter_caminho_drop)

lbl_drop = ctk.CTkLabel(frame_drop, text="\nARRASTE O SEU ARQUIVO .TXT AQUI\n", font=("Roboto", 14, "bold"))
lbl_drop.pack(pady=20)

entry_caminho = ctk.CTkEntry(janela, width=400, placeholder_text="Arquivo selecionado...", state="readonly")
entry_caminho.pack(pady=5)

frame_cfg = ctk.CTkFrame(janela)
frame_cfg.pack(pady=10, padx=40, fill="both", expand=True)

ctk.CTkLabel(frame_cfg, text="Nome do Arquivo:", font=("Roboto", 12, "bold")).pack(pady=(10, 0))
entry_nome_arquivo = ctk.CTkEntry(frame_cfg, width=350, placeholder_text="Ex: Aula_Revisada")
entry_nome_arquivo.pack(pady=(2, 10))

ctk.CTkLabel(frame_cfg, text="Título do Cabeçalho (Topo):", font=("Roboto", 12, "bold")).pack(pady=(5, 0))
entry_topo = ctk.CTkEntry(frame_cfg, width=350, placeholder_text="Ex: Resumo de Estudo")
entry_topo.pack(pady=(2, 10))

ctk.CTkLabel(frame_cfg, text="Texto do Rodapé (Base):", font=("Roboto", 12, "bold")).pack(pady=(5, 0))
entry_rodape = ctk.CTkEntry(frame_cfg, width=350, placeholder_text="Ex: Uso Pessoal")
entry_rodape.pack(pady=(2, 10))

ctk.CTkLabel(frame_cfg, text="Escolha a Fonte:", font=("Roboto", 12, "bold")).pack(pady=(5, 0))
combo_fonte = ctk.CTkComboBox(frame_cfg, values=["helvetica", "Arial", "Verdana", "Times"], width=350)
combo_fonte.set("helvetica")
combo_fonte.pack(pady=(2, 10))

progress_bar = ctk.CTkProgressBar(janela, width=400)
progress_bar.set(0)
progress_bar.pack(pady=15)

btn_gerar = ctk.CTkButton(janela, text="GERAR LIVRO PDF", command=iniciar_processamento, 
                          font=("Roboto", 16, "bold"), height=50, fg_color="#2ECC71", hover_color="#27AE60")
btn_gerar.pack(pady=10)

label_status = ctk.CTkLabel(janela, text="Aguardando arquivo...", font=("Roboto", 12, "italic"))
label_status.pack(pady=10)

janela.mainloop()
