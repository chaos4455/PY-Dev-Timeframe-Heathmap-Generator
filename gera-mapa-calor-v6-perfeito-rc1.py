import os
import hashlib
from datetime import datetime, date, timedelta
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps # ImageOps para possível espelhamento de texto
import tkinter as tk
from tkinter import filedialog
import calendar

# Configurações de Design (Ajustadas para alta densidade e maior resolução)
IMAGE_BACKGROUND_COLOR = (30, 30, 30)
HEATMAP_COLORS = [ # Mantendo a paleta vermelha
    (40, 40, 40),      # Cor para "sem atividade" - Cinza escuro
    (255, 255, 204),   # Amarelo bem claro
    (255, 237, 160),   # Amarelo claro
    (254, 217, 118),   # Amarelo-laranja
    (254, 178, 76),    # Laranja
    (253, 141, 60),    # Laranja-avermelhado
    (252, 78, 42),     # Vermelho-laranja
    (227, 26, 28),     # Vermelho mais forte
    (189, 0, 38),      # Vermelho escuro
    (128, 0, 38)       # Vermelho bem escuro
]

# --- PARÂMETROS CHAVE PARA O LAYOUT DETALHADO FINAL ---
HOUR_SQUARE_SIZE = 8   # TAMANHO AUMENTADO (4x área do anterior que era 4)
HOUR_SQUARE_PADDING = 2 # Padding ajustado
MONTHS_PER_ROW = 4     # Quantos meses (com dados) mostrar lado a lado
DAYS_IN_MONTH_MAX = 31
HOURS_IN_DAY = 24

# --- Margens e Espaçamentos ---
MARGIN_TOP = 120 # Mais espaço para título e legenda
MARGIN_LEFT = 80 # Mais espaço para eixos
MARGIN_RIGHT = 50
MARGIN_BOTTOM = 120 # Mais espaço para legenda inferior
YEAR_LABEL_HEIGHT = 50
MONTH_LABEL_HEIGHT = 40
# Padding entre grades de meses (com dados)
MONTH_GRID_PADDING_X = 30
MONTH_GRID_PADDING_Y = 40
# Padding entre blocos de anos (com dados)
YEAR_BLOCK_PADDING_Y = 60

# --- Fontes ---
FONT_COLOR = (200, 200, 200)
FONT_SIZE_YEAR = 24
FONT_SIZE_MONTH = 18
FONT_SIZE_AXIS = 12 # Aumentado um pouco para acompanhar a resolução
FONT_SIZE_LEGEND = 16
FONT_SIZE_TITLE = 20
FONT_NAME = "arial"
FONT_BOLD_NAME = "arialbd"
FONT_LEGEND_NAME = "arial"
# --- FIM DOS PARÂMETROS DE LAYOUT ---

# Funções auxiliares (calculate_file_hash, get_file_times, count_lines_of_code, scan_directory_for_py_files)
# Mantidas EXATAMENTE como na versão anterior. Omitidas aqui por brevidade.

def calculate_file_hash(filepath):
    """Calcula o hash SHA256 de um arquivo."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Erro ao calcular hash de {filepath}: {e}")
        return None

def get_file_times(filepath):
    """Retorna a data de criação e modificação de um arquivo (datetime objects)."""
    try:
        creation_timestamp = os.path.getctime(filepath)
        modification_timestamp = os.path.getmtime(filepath)
        return datetime.fromtimestamp(creation_timestamp), datetime.fromtimestamp(modification_timestamp)
    except Exception as e:
        print(f"Erro ao obter datas de {filepath}: {e}")
        return None, None

def count_lines_of_code(filepath):
    """Conta o número de linhas de código em um arquivo."""
    try:
        # Tenta detectar encoding comum, senão usa utf-8 ignorando erros
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
        lines = 0
        for enc in encodings_to_try:
            try:
                with open(filepath, 'r', encoding=enc) as file:
                    lines = sum(1 for line in file)
                return lines # Retorna assim que conseguir ler
            except UnicodeDecodeError:
                continue # Tenta o próximo encoding
            except Exception as e_inner:
                # Outro erro durante a leitura (permissão, etc.)
                 print(f"Erro ao contar linhas em {filepath} com encoding {enc}: {e_inner}")
                 return 0 # Retorna 0 se não conseguir ler com nenhum encoding comum

        # Se todos falharem, tenta utf-8 ignorando erros como último recurso
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                lines = sum(1 for line in file)
            return lines
        except Exception as e_final:
            print(f"Erro final ao contar linhas em {filepath}: {e_final}")
            return 0

    except Exception as e:
        print(f"Erro geral ao processar {filepath} para contagem de linhas: {e}")
        return 0


def scan_directory_for_py_files(directory):
    """Varre o diretório em busca de arquivos .py, calcula hash e datas."""
    file_data = []
    unique_files_by_hash = {}
    total_lines = 0

    pastas_ignoradas = set([
        'venv', '.venv', 'env', '.env', 'lib', 'lib64', 'site-packages', 'dist-packages', 'eggs',
        'pip-wheel-metadata', '__pycache__', 'build', 'dist', 'docs', 'doc', 'etc', 'static',
        'templates', 'media', 'node_modules', '.git', '.svn', '.hg', '.CVS', '.idea', '.vscode',
        'spyder-py3', '.pylint.d', '.mypy_cache', '.pytest_cache', '__pypackages__', 'wheelhouse',
        'htmlcov', '.coverage', 'coverage.xml', '*.egg-info', 'MANIFEST', 'sphinx-build', '_build',
        '_static', '_templates', 'data', 'resources', 'assets', 'out', 'output', 'target', 'log',
        'logs', 'tmp', 'temp', 'cache', 'caches', '.gradle', '.mvn', '.docker', '.vagrant', '.terraform',
        'ansible', '.terraform.lock.hcl', '.DS_Store', '.Trashes', '$RECYCLE.BIN', 'System Volume Information',
        '._*', '._.Trashes', '._.DS_Store', '.localized', '.AppleDouble',
    ])
    pastas_para_manter = {'test', 'tests', 'testing', 'integration-tests', 'unit-tests', 'functional-tests', 'benchmark', 'benchmarks', 'example', 'examples', 'sample', 'samples', 'notebooks'}
    pastas_ignoradas = pastas_ignoradas.difference(pastas_para_manter)

    print(f"Iniciando varredura em: {directory}")
    scanned_files_count = 0
    py_files_count = 0

    for pasta_raiz, subpastas, arquivos in os.walk(directory, topdown=True):
        subpastas[:] = [
            subpasta for subpasta in subpastas
            if subpasta.lower() not in pastas_ignoradas and not subpasta.startswith('.')
        ]
        for arquivo in arquivos:
            scanned_files_count += 1
            if arquivo.endswith(".py"):
                py_files_count += 1
                caminho_arquivo = os.path.join(pasta_raiz, arquivo)
                file_hash = calculate_file_hash(caminho_arquivo)
                creation_time, modification_time = get_file_times(caminho_arquivo)

                if file_hash and creation_time and modification_time:
                    is_newer = True
                    if file_hash in unique_files_by_hash:
                        # Garante que a comparação seja feita apenas se o tempo existente for válido
                        existing_mtime = unique_files_by_hash[file_hash].get('modification_time')
                        if isinstance(existing_mtime, datetime) and modification_time <= existing_mtime:
                           is_newer = False

                    if is_newer:
                        lines = count_lines_of_code(caminho_arquivo)
                         # Subtrai linhas antigas apenas se existirem e forem número válido
                        if file_hash in unique_files_by_hash:
                            existing_lines = unique_files_by_hash[file_hash].get('lines')
                            if isinstance(existing_lines, (int, float)):
                                total_lines -= existing_lines

                        unique_files_by_hash[file_hash] = {
                            'creation_time': creation_time,
                            'modification_time': modification_time,
                            'filepath': caminho_arquivo,
                            'lines': lines,
                            'hash': file_hash
                        }
                        # Adiciona novas linhas apenas se for um número válido
                        if isinstance(lines, (int, float)):
                             total_lines += lines

    print(f"Varredura concluída. Total de arquivos escaneados: {scanned_files_count}. Arquivos .py encontrados: {py_files_count}.")
    print(f"Arquivos .py únicos (baseado no hash e mtime): {len(unique_files_by_hash)}.")

    file_data = list(unique_files_by_hash.values())
    return pd.DataFrame(file_data), total_lines, len(unique_files_by_hash)

def draw_simple_rectangle(draw_context, position, size, fill_color):
    """Desenha um retângulo simples."""
    x, y = position
    width, height = size
    # Adicionado +1 na coordenada final para garantir preenchimento completo do pixel
    draw_context.rectangle([x, y, x + width , y + height ], fill=fill_color, outline=None)

def generate_final_detailed_heatmap(
    df_activity_full, # DataFrame com todos os dados
    start_year_input, # Ano inicial fornecido pelo usuário
    time_column,
    output_filepath,
    title_suffix,
    folder_names,
    total_unique_files_overall,
    total_lines_overall
    ):
    """Gera o heatmap final: alta resolução, ano inicial, ignora meses vazios."""

    if df_activity_full.empty or time_column not in df_activity_full.columns:
        print(f"DataFrame vazio ou coluna de tempo '{time_column}' não encontrada. Heatmap não gerado.")
        return

    # 1. Preparação Inicial e Filtro por Ano
    df_activity = df_activity_full.copy() # Trabalha com uma cópia
    df_activity[time_column] = pd.to_datetime(df_activity[time_column], errors='coerce')
    df_activity = df_activity.dropna(subset=[time_column])

    # Filtra pelo ano inicial solicitado
    df_activity = df_activity[df_activity[time_column].dt.year >= start_year_input]

    if df_activity.empty:
        print(f"Nenhuma atividade encontrada a partir do ano {start_year_input} para '{time_column}'. Heatmap não gerado.")
        return

    # Extrair componentes e calcular contagens HORÁRIAS
    df_activity['year'] = df_activity[time_column].dt.year
    df_activity['month'] = df_activity[time_column].dt.month
    df_activity['day'] = df_activity[time_column].dt.day
    df_activity['hour'] = df_activity[time_column].dt.hour
    activity_counts = df_activity.groupby(['year', 'month', 'day', 'hour']).size()

    if activity_counts.empty:
         print(f"Nenhuma contagem de atividade gerada a partir de {start_year_input}. Heatmap não gerado.")
         return

    max_activity_hourly = activity_counts.max()
    print(f"Máxima atividade horária ({title_suffix}, >= {start_year_input}): {max_activity_hourly}")

    # 2. Identificar Anos e Meses *COM DADOS* após o filtro
    years_with_data = sorted(df_activity['year'].unique())
    if not years_with_data:
        print(f"Nenhum ano com dados encontrado a partir de {start_year_input}. Heatmap não gerado.")
        return
    min_year, max_year = years_with_data[0], years_with_data[-1]
    num_years_with_data = len(years_with_data)
    print(f"Anos com dados ({title_suffix}, {min_year}-{max_year}): {num_years_with_data} anos")

    # Obter tuplas (ano, mês) únicas que têm contagens > 0
    active_year_months = sorted(list(activity_counts.index.droplevel([2, 3]).unique()))

    # 3. Configurar Fontes
    try:
        windows_font_dir = r"C:\Windows\Fonts"
        font_year_label = ImageFont.truetype(os.path.join(windows_font_dir, FONT_BOLD_NAME + ".ttf"), FONT_SIZE_YEAR)
        font_month_label = ImageFont.truetype(os.path.join(windows_font_dir, FONT_BOLD_NAME + ".ttf"), FONT_SIZE_MONTH)
        font_axis_label = ImageFont.truetype(os.path.join(windows_font_dir, FONT_NAME + ".ttf"), FONT_SIZE_AXIS)
        font_legend = ImageFont.truetype(os.path.join(windows_font_dir, FONT_LEGEND_NAME + ".ttf"), FONT_SIZE_LEGEND)
        font_title = ImageFont.truetype(os.path.join(windows_font_dir, FONT_BOLD_NAME + ".ttf"), FONT_SIZE_TITLE)
    except IOError:
        print("Fontes Arial não encontradas. Usando fontes padrão.")
        font_year_label, font_month_label, font_axis_label, font_legend, font_title = [ImageFont.load_default()] * 5

    # 4. Calcular Dimensões da Imagem (Layout Dinâmico)
    # Dimensões da grade de UM MÊS (fixas)
    month_grid_width = DAYS_IN_MONTH_MAX * (HOUR_SQUARE_SIZE + HOUR_SQUARE_PADDING) - HOUR_SQUARE_PADDING
    month_grid_height = HOURS_IN_DAY * (HOUR_SQUARE_SIZE + HOUR_SQUARE_PADDING) - HOUR_SQUARE_PADDING

    # Largura total baseada em MONTHS_PER_ROW
    total_content_width = MONTHS_PER_ROW * month_grid_width + max(0, MONTHS_PER_ROW - 1) * MONTH_GRID_PADDING_X
    image_width = MARGIN_LEFT + total_content_width + MARGIN_RIGHT

    # Altura total calculada dinamicamente somando alturas dos anos (que dependem dos meses ativos)
    total_dynamic_height = 0
    year_block_heights = {} # Armazena altura de cada ano para cálculo de offset posterior
    for year in years_with_data:
        active_months_in_year = [m for y, m in active_year_months if y == year]
        num_active_months = len(active_months_in_year)
        if num_active_months == 0:
            year_block_heights[year] = 0
            continue # Pula anos sem meses ativos (não deveria acontecer com a lógica atual, mas seguro)

        num_month_rows_this_year = (num_active_months + MONTHS_PER_ROW - 1) // MONTHS_PER_ROW
        year_content_height = num_month_rows_this_year * (MONTH_LABEL_HEIGHT + month_grid_height) + max(0, num_month_rows_this_year - 1) * MONTH_GRID_PADDING_Y
        current_year_total_height = YEAR_LABEL_HEIGHT + year_content_height
        year_block_heights[year] = current_year_total_height
        total_dynamic_height += current_year_total_height

    image_height = MARGIN_TOP + MARGIN_BOTTOM + total_dynamic_height + max(0, num_years_with_data - 1) * YEAR_BLOCK_PADDING_Y

    print(f"Dimensões FINAIS estimadas da imagem: {int(image_width)} x {int(image_height)} pixels")
    # Aviso mais forte devido à resolução aumentada
    if image_width * image_height > 150_000_000: # Limite mais conservador
         print("\n!!! AVISO MUITO SÉRIO !!!")
         print("A imagem resultante será EXTREMAMENTE GRANDE devido à alta resolução e período.")
         print("A geração pode consumir GIGABYTES de RAM e/ou FALHAR.")
         print("Considere usar um ano inicial mais recente ou reduzir MONTHS_PER_ROW / HOUR_SQUARE_SIZE.")
         confirm = input("Deseja continuar mesmo assim? (s/N): ")
         if confirm.lower() != 's':
             print("Geração cancelada.")
             return

    # 5. Criar Imagem e Desenhar Elementos Estáticos
    image = Image.new('RGB', (int(image_width), int(image_height)), IMAGE_BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    # Título Principal
    title_text = f"Heatmap Horário Detalhado Final ({title_suffix}, {min_year}-{max_year})"
    try: title_w = draw.textlength(title_text, font=font_title)
    except: title_w = draw.textbbox((0,0), title_text, font=font_title)[2]
    title_x = MARGIN_LEFT + (total_content_width - title_w) / 2
    title_y = 30
    draw.text((title_x, title_y), title_text, font=font_title, fill=FONT_COLOR)

    # Legenda Superior de Cores
    legend_y_start = title_y + font_title.getmetrics()[0] + 25
    legend_x = MARGIN_LEFT
    legend_texts = [
        (f"Mais ({max_activity_hourly}+/h)", HEATMAP_COLORS[-1]),
        ("Médio", HEATMAP_COLORS[len(HEATMAP_COLORS)//2]),
        ("Menos (1/h)", HEATMAP_COLORS[1]),
        ("Sem Atividade", HEATMAP_COLORS[0]),
    ]
    temp_x = legend_x
    try: label_w = draw.textlength("Atividade Horária: ", font=font_legend)
    except: label_w = draw.textbbox((0,0),"Atividade Horária: ", font=font_legend)[2]
    draw.text((temp_x, legend_y_start), "Atividade Horária:", font=font_legend, fill=FONT_COLOR)
    temp_x += label_w + 15
    LEGEND_COLOR_SQUARE_SIZE = FONT_SIZE_LEGEND # Ajusta tamanho do quadrado da legenda

    for text, color in reversed(legend_texts):
         draw.rectangle(
             [temp_x, legend_y_start + (font_legend.getmetrics()[0] - LEGEND_COLOR_SQUARE_SIZE) // 2,
              temp_x + LEGEND_COLOR_SQUARE_SIZE, legend_y_start + (font_legend.getmetrics()[0] + LEGEND_COLOR_SQUARE_SIZE) // 2],
             fill=color )
         temp_x += LEGEND_COLOR_SQUARE_SIZE + 8
         try: text_w = draw.textlength(text, font=font_legend)
         except: text_w = draw.textbbox((0,0), text, font=font_legend)[2]
         draw.text((temp_x, legend_y_start), text, font=font_legend, fill=FONT_COLOR)
         temp_x += text_w + 20

    # 6. Desenhar Blocos Anuais (Apenas com meses ativos)
    current_y_offset = MARGIN_TOP # Começa abaixo do título/legenda

    for year in years_with_data:
        print(f"Desenhando ano: {year}...")
        year_start_y = current_y_offset
        active_months_in_year = sorted([m for y, m in active_year_months if y == year])

        if not active_months_in_year: # Segurança, não deve ocorrer
            current_y_offset += YEAR_BLOCK_PADDING_Y # Pula espaço se ano ficou vazio
            continue

        # Desenha Rótulo do Ano
        year_text = str(year)
        try: year_text_w = draw.textlength(year_text, font=font_year_label)
        except: year_text_w = draw.textbbox((0,0), year_text, font=font_year_label)[2]
        year_label_x = MARGIN_LEFT + (total_content_width - year_text_w) / 2
        year_label_y = year_start_y
        draw.text((year_label_x, year_label_y), year_text, font=font_year_label, fill=FONT_COLOR)

        current_month_base_y = year_start_y + YEAR_LABEL_HEIGHT

        # --- Desenhar Grades Mensais ATIVAS dentro do Ano ---
        for active_month_idx, month in enumerate(active_months_in_year):
            month_row_index = active_month_idx // MONTHS_PER_ROW
            month_col_index = active_month_idx % MONTHS_PER_ROW

            # Calcula posição X e Y da grade deste mês ATIVO
            month_start_x = MARGIN_LEFT + month_col_index * (month_grid_width + MONTH_GRID_PADDING_X)
            month_start_y = current_month_base_y + month_row_index * (MONTH_LABEL_HEIGHT + month_grid_height + MONTH_GRID_PADDING_Y)

            # Desenha Rótulo do Mês
            month_name = date(year, month, 1).strftime('%B') # Nome completo
            try: month_text_w = draw.textlength(month_name, font=font_month_label)
            except: month_text_w = draw.textbbox((0,0), month_name, font=font_month_label)[2]
            month_label_x = month_start_x + (month_grid_width - month_text_w) / 2
            month_label_y = month_start_y
            draw.text((month_label_x, month_label_y), month_name, font=font_month_label, fill=FONT_COLOR)

            grid_start_y = month_start_y + MONTH_LABEL_HEIGHT

            # Desenha Rótulos de Eixo (Hora/Dia) - com mais espaçamento
            if month_col_index == 0: # Horas à esquerda da primeira coluna de meses
                for hr in range(0, 24, 4): # 0h, 4h, 8h ... 20h
                    hour_text = f"{hr:02d}h"
                    try: text_h = font_axis_label.getmetrics()[0]
                    except: text_h = 10
                    text_y = grid_start_y + hr * (HOUR_SQUARE_SIZE + HOUR_SQUARE_PADDING) + (HOUR_SQUARE_SIZE - text_h // 2)
                    draw.text((MARGIN_LEFT - 35, text_y), hour_text, font=font_axis_label, fill=FONT_COLOR, anchor="lm")

            # Dias abaixo da grade
            day_label_y = grid_start_y + month_grid_height + 10
            days_to_label = [1, 10, 20, DAYS_IN_MONTH_MAX]
            for day_label in days_to_label:
                 col = day_label - 1
                 text_x = month_start_x + col * (HOUR_SQUARE_SIZE + HOUR_SQUARE_PADDING) + HOUR_SQUARE_SIZE / 2
                 draw.text((text_x, day_label_y), str(day_label), font=font_axis_label, fill=FONT_COLOR, anchor="mt")

            # --- Desenhar quadrados de Hora/Dia para o mês ativo ---
            days_in_this_month = calendar.monthrange(year, month)[1]
            for day in range(1, days_in_this_month + 1): # Itera só até o dia real do mês
                for hour in range(HOURS_IN_DAY):
                    pixel_x = month_start_x + (day - 1) * (HOUR_SQUARE_SIZE + HOUR_SQUARE_PADDING)
                    pixel_y = grid_start_y + hour * (HOUR_SQUARE_SIZE + HOUR_SQUARE_PADDING)

                    count = activity_counts.get((year, month, day, hour), 0)
                    color_index = 0
                    if count > 0:
                        color_index = min(count, len(HEATMAP_COLORS) - 1)
                        if color_index == 0: color_index = 1 # Garante que 1 tenha cor > 0
                    fill_color = HEATMAP_COLORS[color_index]

                    draw_simple_rectangle(draw, (pixel_x, pixel_y), (HOUR_SQUARE_SIZE, HOUR_SQUARE_SIZE), fill_color)

        # Atualiza o offset Y para o próximo ano usando a altura calculada ANTES
        current_y_offset += year_block_heights[year] + YEAR_BLOCK_PADDING_Y

    # 7. Desenhar Legenda Inferior
    legend_bottom_y = image_height - MARGIN_BOTTOM + 30 # Posição
    folder_names_text = ", ".join(folder_names)
    folders_scanned_text = f"Pastas: {folder_names_text}"
    total_files_text = f"Arquivos .py Únicos: {total_unique_files_overall}"
    total_lines_text = f"Linhas de Código: {total_lines_overall:,}".replace(",",".")
    date_range_text = f"Período Exibido: {min_year} - {max_year} ({title_suffix})"

    draw.text((MARGIN_LEFT, legend_bottom_y), date_range_text, font=font_legend, fill=FONT_COLOR)
    draw.text((MARGIN_LEFT, legend_bottom_y + FONT_SIZE_LEGEND + 8), folders_scanned_text, font=font_legend, fill=FONT_COLOR)
    draw.text((MARGIN_LEFT, legend_bottom_y + 2 * (FONT_SIZE_LEGEND + 8)), total_files_text, font=font_legend, fill=FONT_COLOR)
    draw.text((MARGIN_LEFT, legend_bottom_y + 3 * (FONT_SIZE_LEGEND + 8)), total_lines_text, font=font_legend, fill=FONT_COLOR)

    # 8. Salvar Imagem
    try:
        image.save(output_filepath, quality=95) # Pode ajustar quality para PNG se suportado ou omitir
        print(f"Heatmap final detalhado ({title_suffix}) gerado como {output_filepath}")
    except Exception as e:
        print(f"Erro CRÍTICO ao salvar a imagem {output_filepath}: {e}")
        if isinstance(e, (MemoryError, ValueError)):
             print("Provavelmente causado pelo tamanho excessivo da imagem. Tente um período menor ou resolução menor.")

# --- Função Principal ---
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    directory_paths = []
    while True:
        path = filedialog.askdirectory(title=f"Selecione a pasta #{len(directory_paths) + 1} (Cancele para parar)")
        if not path:
            if not directory_paths:
                print("Nenhuma pasta selecionada. Saindo.")
                exit()
            else:
                break
        directory_paths.append(path)

    # --- Pergunta o Ano Inicial ---
    current_actual_year = datetime.now().year
    while True:
        try:
            year_input_str = input(f"Digite o ANO INICIAL para o heatmap (ex: 2020, deixe em branco para começar do mais antigo encontrado): ")
            if not year_input_str:
                start_year_requested = 0 # Indica para usar o mínimo encontrado
                print("Ok, começando do ano mais antigo encontrado nos dados.")
                break
            start_year_requested = int(year_input_str)
            if 1970 <= start_year_requested <= current_actual_year + 1: # Range razoável
                print(f"Ok, começando a partir do ano {start_year_requested}.")
                break
            else:
                print(f"Ano inválido. Por favor, insira um ano entre 1970 e {current_actual_year + 1}.")
        except ValueError:
            print("Entrada inválida. Por favor, digite um número de ano.")
    # -----------------------------

    # (Lógica de agregação de arquivos únicos mantida)
    overall_unique_files = {}
    overall_total_lines = 0
    folder_base_names = []

    for i, dir_path in enumerate(directory_paths):
        folder_base_names.append(os.path.basename(dir_path))
        print(f"\n--- Varrendo pasta {i+1}: {dir_path} ---")
        df_files, _, _ = scan_directory_for_py_files(dir_path)

        for index, row in df_files.iterrows():
             file_hash = row.get('hash')
             modification_time = row.get('modification_time')
             lines = row.get('lines')

             # Validação básica dos dados da linha
             if not file_hash or not isinstance(modification_time, datetime) or not isinstance(lines, (int, float)):
                 # print(f"Aviso: Dados inválidos ou ausentes para linha {index}. Pulando.")
                 continue # Pula linha se dados essenciais faltam ou tipo incorreto

             is_newer_overall = True
             if file_hash in overall_unique_files:
                  existing_mtime = overall_unique_files[file_hash].get('modification_time')
                  if isinstance(existing_mtime, datetime) and modification_time <= existing_mtime:
                       is_newer_overall = False

             if is_newer_overall:
                  if file_hash in overall_unique_files:
                       existing_lines = overall_unique_files[file_hash].get('lines')
                       if isinstance(existing_lines, (int, float)):
                            overall_total_lines -= existing_lines

                  overall_unique_files[file_hash] = row.to_dict()
                  overall_total_lines += lines

    unique_files_df_combined = pd.DataFrame(list(overall_unique_files.values()))
    total_unique_files_combined = len(unique_files_df_combined)

    if not unique_files_df_combined.empty:
        if 'creation_time' in unique_files_df_combined.columns:
            unique_files_df_combined['creation_time'] = pd.to_datetime(unique_files_df_combined['creation_time'], errors='coerce')
        if 'modification_time' in unique_files_df_combined.columns:
            unique_files_df_combined['modification_time'] = pd.to_datetime(unique_files_df_combined['modification_time'], errors='coerce')

        # Determina o ano inicial real se o usuário não especificou
        min_year_found_c = unique_files_df_combined['creation_time'].dt.year.min() if 'creation_time' in unique_files_df_combined.columns and not unique_files_df_combined['creation_time'].isnull().all() else float('inf')
        min_year_found_m = unique_files_df_combined['modification_time'].dt.year.min() if 'modification_time' in unique_files_df_combined.columns and not unique_files_df_combined['modification_time'].isnull().all() else float('inf')
        min_year_found = int(min(min_year_found_c, min_year_found_m))

        if start_year_requested == 0: # Se usuário não especificou, usa o mínimo encontrado
             actual_start_year = min_year_found if min_year_found != float('inf') else current_actual_year
             print(f"Ano mais antigo encontrado: {actual_start_year}. Usando como início.")
        else: # Usuário especificou, usa o que ele pediu
             actual_start_year = start_year_requested


        print("\n--- Resumo da Varredura Combinada ---")
        print(f"Total de arquivos .py únicos encontrados: {total_unique_files_combined}")
        print(f"Total de linhas de código nesses arquivos: {overall_total_lines:,}".replace(",","."))
        print(f"Heatmap será gerado a partir do ano: {actual_start_year}")

        # Cria a pasta de saída
        folder_name_for_output = "_".join(folder_base_names)
        folder_hash_combined = hashlib.sha256(folder_name_for_output.encode()).hexdigest()[:8]
        output_folder_name = f"heatmap_{folder_name_for_output}_{folder_hash_combined}_final_detailed"
        output_folder_path = os.path.join("output_heatmaps_final_detailed", output_folder_name) # Nova pasta
        os.makedirs(output_folder_path, exist_ok=True)
        print(f"\nHeatmaps finais detalhados serão salvos em: {output_folder_path}")

        # Gerar heatmap FINAL DETALHADO para CREATED times
        output_filename_created = f"heatmap_{folder_name_for_output}_{folder_hash_combined}_created_final.png"
        output_filepath_created = os.path.join(output_folder_path, output_filename_created)
        if 'creation_time' in unique_files_df_combined.columns:
            generate_final_detailed_heatmap(
                unique_files_df_combined,
                actual_start_year,
                'creation_time',
                output_filepath_created,
                'Criados',
                folder_base_names,
                total_unique_files_combined,
                overall_total_lines
            )
        else:
            print("Coluna 'creation_time' não encontrada. Pulando heatmap de criados.")

        # Gerar heatmap FINAL DETALHADO para MODIFIED times
        output_filename_modified = f"heatmap_{folder_name_for_output}_{folder_hash_combined}_modified_final.png"
        output_filepath_modified = os.path.join(output_folder_path, output_filename_modified)
        if 'modification_time' in unique_files_df_combined.columns:
            generate_final_detailed_heatmap(
                unique_files_df_combined,
                actual_start_year,
                'modification_time',
                output_filepath_modified,
                'Modificados',
                folder_base_names,
                total_unique_files_combined,
                overall_total_lines
            )
        else:
            print("Coluna 'modification_time' não encontrada. Pulando heatmap de modificados.")


        print(f"\nProcesso completo. Heatmaps PNG finais detalhados gerados em: {output_folder_path}")
    else:
        print("\nNenhum arquivo .py único encontrado ou dados de tempo inválidos nas pastas especificadas.")