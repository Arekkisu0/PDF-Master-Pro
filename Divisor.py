import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import time
import subprocess
import threading
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from tkinterdnd2 import DND_FILES, TkinterDnD
import warnings
import ollama

# Tenta importar psutil para monitorar hardware (instale com: pip install psutil)
try:
    import psutil
except ImportError:
    psutil = None

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Variável global para controlar o monitoramento
processando = False

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
    bg_color = ctk.ThemeManager.theme["CTk"]["fg_color"]
    janela.configure(bg=bg_color[1] if mode == "dark" else bg_color[0])

def obter_caminho_drop(event):
    path = event.data.strip('{}')
    entry_caminho.configure(state="normal")
    entry_caminho.delete(0, ctk.END)
    entry_caminho.insert(0, path)
    entry_caminho.configure(state="readonly")

# --- FUNÇÕES DE MONITORAMENTO ---
def formatar_tempo(segundos):
    m, s = divmod(int(segundos), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def monitorar_hardware(inicio_tempo):
    while processando:
        # Tempo
        tempo_decorrido = time.time() - inicio_tempo
        texto_tempo = formatar_tempo(tempo_decorrido)
        
        # CPU
        uso_cpu = f"{psutil.cpu_percent()}%" if psutil else "N/A"
        
        # GPU (NVIDIA via linha de comando para não precisar de libs extras complexas)
        uso_gpu = "0%"
        try:
            cmd = "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits"
            uso_gpu = subprocess.check_output(cmd, shell=True).decode('utf-8').strip() + "%"
        except:
            uso_gpu = "N/A"

        # Atualiza Interface
        janela.after(0, lambda t=texto_tempo, c=uso_cpu, g=uso_gpu: atualizar_labels_info(t, c, g))
        time.sleep(1)

def atualizar_labels_info(tempo, cpu, gpu):
    lbl_tempo_val.configure(text=tempo)
    lbl_cpu_val.configure(text=cpu)
    lbl_gpu_val.configure(text=gpu)

# --- LÓGICA PRINCIPAL ---
def tarefa_pesada(caminho_txt, nome_base, modo_ia, pasta_destino, dados_pdf):
    global processando
    processando = True
    inicio = time.time()
    
    # Inicia thread de monitoramento em paralelo
    thread_mon = threading.Thread(target=monitorar_hardware, args=(inicio,))
    thread_mon.daemon = True
    thread_mon.start()

    try:
        with open(caminho_txt, "r", encoding="utf-8") as f:
            texto_bruto = f.read()

        TAMANHO_MAXIMO = 2500 
        idx_txt, partes = 0, []
        while idx_txt < len(texto_bruto):
            fim = min(idx_txt + TAMANHO_MAXIMO, len(texto_bruto))
            if fim < len(texto_bruto):
                ponto = texto_bruto.rfind('.', idx_txt, fim)
                fim = ponto + 1 if ponto != -1 and ponto > idx_txt else fim
            partes.append(texto_bruto[idx_txt:fim].strip())
            idx_txt = fim

        pdf = PDF_Customizavel(dados_pdf['topo'], dados_pdf['rodape'], dados_pdf['fonte'])
        pdf.set_left_margin(20)
        pdf.set_right_margin(20)
        pdf.add_page()

        texto_final_acumulado = ""
        total = len(partes)

        for i, conteudo in enumerate(partes):
            if switch_ia.get() == 1:
                janela.after(0, lambda: label_status.configure(text=f"Processando parte {i+1}/{total}", text_color="#A29BFE"))
                
                if modo_ia == "Apenas Corrigir":
                    instrucao = "Revisor: Corrija pontuação e gramática. Apenas o texto."
                elif modo_ia == "Inglês -> Português":
                    instrucao = "Tradutor: Inglês para Português BR. Fiel e fluído. Apenas o texto."
                else:
                    instrucao = "Translator: PT to EN. Formal and accurate. Text only."

                response = ollama.chat(
                    model='llama3', 
                    messages=[
                        {'role': 'system', 'content': f"{instrucao} Sem introduções. Saída pura."},
                        {'role': 'user', 'content': conteudo}
                    ],
                    options={
                        "temperature": 0.2, 
                    }
                )
                conteudo = response['message']['content'].strip().strip('"').strip("'")

            texto_final_acumulado += conteudo + "\n\n"

            pdf.set_font(pdf.fonte_pdf, "B", 16)
            pdf.cell(0, 15, f"Parte {i+1}", align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 170, pdf.get_y())
            pdf.ln(5)
            pdf.set_font(pdf.fonte_pdf, size=11)
            pdf.multi_cell(0, 7, text=limpar_texto_para_pdf(conteudo), align="J")
            pdf.ln(10)
            
            janela.after(0, lambda v=(i + 1) / total: progress_bar.set(v))

        pdf.output(os.path.join(pasta_destino, f"{nome_base}.pdf"))
        with open(os.path.join(pasta_destino, f"{nome_base}_REVISADO.txt"), "w", encoding="utf-8") as f_out:
            f_out.write(texto_final_acumulado)

        processando = False # Para o monitoramento
        janela.after(0, lambda: label_status.configure(text="Concluído!", text_color="#2ECC71"))
        janela.after(0, lambda: btn_gerar.configure(state="normal"))
        
        tempo_total = formatar_tempo(time.time() - inicio)
        messagebox.showinfo("Sucesso", f"Finalizado em {tempo_total}!")

    except Exception as e:
        processando = False
        janela.after(0, lambda: label_status.configure(text="Erro crítico.", text_color="#E74C3C"))
        janela.after(0, lambda: btn_gerar.configure(state="normal"))
        messagebox.showerror("Erro", str(e))

def iniciar_processamento():
    caminho_txt = entry_caminho.get()
    nome_base = entry_nome_arquivo.get().strip()
    
    if not caminho_txt or not os.path.exists(caminho_txt):
        messagebox.showwarning("Erro", "Arraste um arquivo .txt!")
        return
    if not nome_base:
        messagebox.showwarning("Erro", "Dê um nome ao arquivo!")
        return
    pasta_destino = filedialog.askdirectory(title="Onde salvar?")
    if not pasta_destino: return

    btn_gerar.configure(state="disabled")
    label_status.configure(text="Iniciando motores...", text_color="#3B8ED0")
    
    dados_pdf = {'topo': entry_topo.get(), 'rodape': entry_rodape.get(), 'fonte': combo_fonte.get()}

    thread = threading.Thread(target=tarefa_pesada, args=(caminho_txt, nome_base, combo_ia.get(), pasta_destino, dados_pdf))
    thread.daemon = True
    thread.start()

# --- INTERFACE ---
janela = TkinterDnD.Tk()
ctk.set_appearance_mode("dark")
janela.title("PDF Master Pro v6.0 - Dashboard")
janela.geometry("550x950")

bg_color = ctk.ThemeManager.theme["CTk"]["fg_color"]
janela.configure(bg=bg_color[1]) 

frame_top = ctk.CTkFrame(janela, fg_color="transparent")
frame_top.pack(pady=10, padx=20, fill="x")
switch_ia = ctk.CTkSwitch(frame_top, text="Ativar IA (Llama 3)", progress_color="#A29BFE")
switch_ia.pack(side="left")
switch_tema = ctk.CTkSwitch(frame_top, text="Modo Claro", command=alternar_tema)
switch_tema.pack(side="right")

ctk.CTkLabel(janela, text="EDITOR DE LIVROS PDF", font=("Roboto", 24, "bold")).pack(pady=5)

# --- PAINEL DE MONITORAMENTO ---
frame_monitor = ctk.CTkFrame(janela, fg_color="#2B2B2B", corner_radius=10)
frame_monitor.pack(pady=5, padx=40, fill="x")

# Colunas do monitor
col1 = ctk.CTkFrame(frame_monitor, fg_color="transparent")
col1.pack(side="left", expand=True, padx=10, pady=5)
ctk.CTkLabel(col1, text="Tempo", font=("Roboto", 10)).pack()
lbl_tempo_val = ctk.CTkLabel(col1, text="00:00:00", font=("Roboto", 16, "bold"), text_color="#E74C3C")
lbl_tempo_val.pack()

col2 = ctk.CTkFrame(frame_monitor, fg_color="transparent")
col2.pack(side="left", expand=True, padx=10, pady=5)
ctk.CTkLabel(col2, text="CPU", font=("Roboto", 10)).pack()
lbl_cpu_val = ctk.CTkLabel(col2, text="0%", font=("Roboto", 16, "bold"), text_color="#3B8ED0")
lbl_cpu_val.pack()

col3 = ctk.CTkFrame(frame_monitor, fg_color="transparent")
col3.pack(side="left", expand=True, padx=10, pady=5)
ctk.CTkLabel(col3, text="GPU (RTX)", font=("Roboto", 10)).pack()
lbl_gpu_val = ctk.CTkLabel(col3, text="0%", font=("Roboto", 16, "bold"), text_color="#2ECC71")
lbl_gpu_val.pack()
# -----------------------------

frame_drop = ctk.CTkFrame(janela, border_width=2, border_color="#3B8ED0")
frame_drop.pack(pady=10, padx=40, fill="x")
frame_drop.drop_target_register(DND_FILES)
frame_drop.dnd_bind('<<Drop>>', obter_caminho_drop)
ctk.CTkLabel(frame_drop, text="\nARRASTE O .TXT AQUI\n", font=("Roboto", 14, "bold")).pack(pady=20)

entry_caminho = ctk.CTkEntry(janela, width=400, state="readonly")
entry_caminho.pack(pady=5)

frame_cfg = ctk.CTkFrame(janela)
frame_cfg.pack(pady=10, padx=40, fill="both", expand=True)

ctk.CTkLabel(frame_cfg, text="Nome do Arquivo:").pack(pady=(5,0))
entry_nome_arquivo = ctk.CTkEntry(frame_cfg, width=350)
entry_nome_arquivo.pack()

ctk.CTkLabel(frame_cfg, text="Título Cabeçalho:").pack(pady=(5,0))
entry_topo = ctk.CTkEntry(frame_cfg, width=350)
entry_topo.pack()

ctk.CTkLabel(frame_cfg, text="Texto do Rodapé:").pack(pady=(5,0))
entry_rodape = ctk.CTkEntry(frame_cfg, width=350)
entry_rodape.pack()

ctk.CTkLabel(frame_cfg, text="Fonte:").pack(pady=(5,0))
combo_fonte = ctk.CTkComboBox(frame_cfg, values=["helvetica", "Arial", "Times"], width=350)
combo_fonte.set("helvetica")
combo_fonte.pack()

ctk.CTkLabel(frame_cfg, text="Tarefa da IA:").pack(pady=(5, 0))
combo_ia = ctk.CTkComboBox(frame_cfg, values=["Apenas Corrigir", "Inglês -> Português", "Português -> Inglês"], width=350)
combo_ia.set("Apenas Corrigir")
combo_ia.pack()

progress_bar = ctk.CTkProgressBar(janela, width=400)
progress_bar.set(0)
progress_bar.pack(pady=20)

btn_gerar = ctk.CTkButton(janela, text="GERAR ARQUIVOS", command=iniciar_processamento, height=50, fg_color="#2ECC71", font=("Roboto", 16, "bold"))
btn_gerar.pack(pady=10)

label_status = ctk.CTkLabel(janela, text="Sistema pronto.")
label_status.pack(pady=5)

if not psutil:
    messagebox.showwarning("Aviso", "Instale o psutil (pip install psutil) para ver o uso da CPU!")

janela.mainloop()