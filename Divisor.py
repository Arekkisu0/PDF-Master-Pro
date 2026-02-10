import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from tkinterdnd2 import DND_FILES, TkinterDnD
import warnings
import ollama

warnings.filterwarnings("ignore", category=DeprecationWarning)

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
            except: self.fonte_pdf = "helvetica"

    def header(self):
        self.set_font(self.fonte_pdf, "I", 8)
        self.cell(0, 10, self.titulo_topo, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.fonte_pdf, "I", 8)
        self.cell(0, 10, f"{self.texto_rodape} - Página {self.page_no()}", align="C")

def limpar_texto_para_pdf(texto):
    subs = {"—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "\u2022": "-", "\u2014": "-"}
    for k, v in subs.items(): texto = texto.replace(k, v)
    return texto.encode('latin-1', 'replace').decode('latin-1')

def alternar_tema():
    mode = "light" if switch_tema.get() == 1 else "dark"
    ctk.set_appearance_mode(mode)
    # Força a atualização da cor de fundo da janela raiz para evitar o fundo branco
    bg_color = ctk.ThemeManager.theme["CTk"]["fg_color"]
    janela.configure(bg=bg_color[1] if mode == "dark" else bg_color[0])

def obter_caminho_drop(event):
    path = event.data.strip('{}')
    entry_caminho.configure(state="normal")
    entry_caminho.delete(0, ctk.END)
    entry_caminho.insert(0, path)
    entry_caminho.configure(state="readonly")

def iniciar_processamento():
    caminho_txt = entry_caminho.get()
    nome_base = entry_nome_arquivo.get().strip()
    modo_ia = combo_ia.get()
    
    if not caminho_txt or not os.path.exists(caminho_txt):
        messagebox.showwarning("Erro", "Arraste um arquivo .txt!")
        return
    if not nome_base:
        messagebox.showwarning("Erro", "Dê um nome ao arquivo!")
        return

    pasta_destino = filedialog.askdirectory(title="Onde salvar os arquivos?")
    if not pasta_destino: return

    try:
        label_status.configure(text="Status: Lendo...", text_color="#3B8ED0")
        janela.update()

        with open(caminho_txt, "r", encoding="utf-8") as f:
            texto_bruto = f.read()

        TAMANHO_MAXIMO = 5000 
        inicio, partes = 0, []
        while inicio < len(texto_bruto):
            fim = min(inicio + TAMANHO_MAXIMO, len(texto_bruto))
            if fim < len(texto_bruto):
                ponto = texto_bruto.rfind('.', inicio, fim)
                fim = ponto + 1 if ponto != -1 and ponto > inicio else fim
            partes.append(texto_bruto[inicio:fim].strip())
            inicio = fim

        pdf = PDF_Customizavel(entry_topo.get(), entry_rodape.get(), combo_fonte.get())
        pdf.set_left_margin(20)
        pdf.set_right_margin(20)
        pdf.add_page()

        texto_final_acumulado = ""
        total = len(partes)

        for i, conteudo in enumerate(partes):
            if switch_ia.get() == 1:
                label_status.configure(text=f"IA: {modo_ia} ({i+1}/{total})", text_color="#A29BFE")
                janela.update()
                
                prompt_task = "Corrija apenas pontuação e erros gramaticais."
                if modo_ia == "Inglês -> Português":
                    prompt_task = "Traduza para Português do Brasil e corrija a pontuação."
                elif modo_ia == "Português -> Inglês":
                    prompt_task = "Translate to English and correct punctuation."

                response = ollama.chat(model='llama3', messages=[
                    {'role': 'system', 'content': f"Você é um motor de texto. {prompt_task} Retorne APENAS o texto resultante. Proibido introduções ou comentários."},
                    {'role': 'user', 'content': conteudo}
                ])
                conteudo = response['message']['content'].strip().strip('"')

            texto_final_acumulado += conteudo + "\n\n"

            pdf.set_font(pdf.fonte_pdf, "B", 16)
            pdf.cell(0, 15, f"Parte {i+1}", align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 170, pdf.get_y())
            pdf.ln(5)
            pdf.set_font(pdf.fonte_pdf, size=11)
            pdf.multi_cell(0, 7, text=limpar_texto_para_pdf(conteudo), align="J")
            pdf.ln(10)
            
            progress_bar.set((i + 1) / total)
            janela.update()

        pdf.output(os.path.join(pasta_destino, f"{nome_base}.pdf"))
        
        with open(os.path.join(pasta_destino, f"{nome_base}_REVISADO.txt"), "w", encoding="utf-8") as f_out:
            f_out.write(texto_final_acumulado)

        label_status.configure(text="Status: Concluído!", text_color="#2ECC71")
        messagebox.showinfo("Sucesso", "PDF e TXT gerados com sucesso!")

    except Exception as e:
        label_status.configure(text="Status: Erro.", text_color="#E74C3C")
        messagebox.showerror("Erro", str(e))

# --- INTERFACE ---
janela = TkinterDnD.Tk()
ctk.set_appearance_mode("dark")
janela.title("PDF Master Pro v4.8 - AI Translator")
janela.geometry("550x950")

# Força a cor de fundo da janela principal (ROOT)
bg_color = ctk.ThemeManager.theme["CTk"]["fg_color"]
janela.configure(bg=bg_color[1]) 

frame_top = ctk.CTkFrame(janela, fg_color="transparent")
frame_top.pack(pady=10, padx=20, fill="x")

switch_ia = ctk.CTkSwitch(frame_top, text="Ativar IA (Llama 3)", progress_color="#A29BFE")
switch_ia.pack(side="left")

switch_tema = ctk.CTkSwitch(frame_top, text="Modo Claro", command=alternar_tema)
switch_tema.pack(side="right")

lbl_titulo = ctk.CTkLabel(janela, text="EDITOR DE LIVROS PDF", font=("Roboto", 24, "bold"))
lbl_titulo.pack(pady=10)

frame_drop = ctk.CTkFrame(janela, border_width=2, border_color="#3B8ED0")
frame_drop.pack(pady=10, padx=40, fill="x")
frame_drop.drop_target_register(DND_FILES)
frame_drop.dnd_bind('<<Drop>>', obter_caminho_drop)

ctk.CTkLabel(frame_drop, text="\nARRASTE O .TXT AQUI\n", font=("Roboto", 14, "bold")).pack(pady=20)

entry_caminho = ctk.CTkEntry(janela, width=400, state="readonly", placeholder_text="Aguardando arquivo...")
entry_caminho.pack(pady=5)

# Frame de configurações com cor adaptável
frame_cfg = ctk.CTkFrame(janela)
frame_cfg.pack(pady=10, padx=40, fill="both", expand=True)

# Campos de entrada
ctk.CTkLabel(frame_cfg, text="Nome do Arquivo:", font=("Roboto", 12, "bold")).pack(pady=(10,0))
entry_nome_arquivo = ctk.CTkEntry(frame_cfg, width=350, placeholder_text="Ex: meu_livro_final")
entry_nome_arquivo.pack()

ctk.CTkLabel(frame_cfg, text="Título Cabeçalho:", font=("Roboto", 12, "bold")).pack(pady=(5,0))
entry_topo = ctk.CTkEntry(frame_cfg, width=350, placeholder_text="Ex: Transcrição de Aula")
entry_topo.pack()

ctk.CTkLabel(frame_cfg, text="Fonte:", font=("Roboto", 12, "bold")).pack(pady=(5,0))
combo_fonte = ctk.CTkComboBox(frame_cfg, values=["helvetica", "Arial", "Times"], width=350)
combo_fonte.set("helvetica")
combo_fonte.pack()

ctk.CTkLabel(frame_cfg, text="Tarefa da IA:", font=("Roboto", 12, "bold")).pack(pady=(10, 0))
combo_ia = ctk.CTkComboBox(frame_cfg, values=["Apenas Corrigir", "Inglês -> Português", "Português -> Inglês"], width=350)
combo_ia.set("Apenas Corrigir")
combo_ia.pack()

progress_bar = ctk.CTkProgressBar(janela, width=400)
progress_bar.set(0)
progress_bar.pack(pady=25)

btn_gerar = ctk.CTkButton(janela, text="GERAR ARQUIVOS", command=iniciar_processamento, 
                          height=50, font=("Roboto", 16, "bold"), fg_color="#2ECC71", hover_color="#27AE60")
btn_gerar.pack(pady=10)

label_status = ctk.CTkLabel(janela, text="Pronto para começar", font=("Roboto", 12, "italic"))
label_status.pack(pady=10)

janela.mainloop()