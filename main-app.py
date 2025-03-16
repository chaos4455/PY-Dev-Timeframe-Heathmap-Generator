import os
import hashlib
from datetime import datetime, date, timedelta
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# Configurações de Design 100% Compatíveis com a Imagem de Exemplo
IMAGE_BACKGROUND_COLOR = (30, 30, 30)
HEATMAP_COLORS = [
    (40, 40, 40),
    (64, 160, 64),
    (80, 208, 80),
    (96, 240, 96),
    (128, 255, 128),
    (160, 255, 160),
]
SQUARE_SIZE = 16
SQUARE_PADDING = 4
SQUARE_CORNER_RADIUS = 2
GRID_LINE_COLOR = (50, 50, 50)
GRID_LINE_WIDTH = 1
MARGIN_TOP = 80
MARGIN_LEFT = 80
MARGIN_RIGHT = 80
MARGIN_BOTTOM = 80
MONTH_LABEL_MARGIN = 25
DAY_LABEL_MARGIN_LEFT = 5
YEAR_LABEL_MARGIN_TOP = 30
YEAR_LABEL_MARGIN_BOTTOM = 40  # <---  DEFINIÇÃO DE YEAR_LABEL_MARGIN_BOTTOM AQUI (estava faltando ou comentada)
YEAR_LABEL_WIDTH = 40
YEAR_BLOCK_PADDING = 60

FONT_COLOR = (200, 200, 200)
FONT_SIZE_MONTH = 20
FONT_SIZE_YEAR = 24
FONT_SIZE_DAY = 12
FONT_DAY_OF_WEEK_NAME = "arialbd" # Nome da fonte Arial Bold (sem extensão)
FONT_NAME = "arial" # Nome da fonte Arial (sem extensão)


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

def get_original_creation_time(filepath):
    """Retorna a data de criação original de um arquivo (datetime object)."""
    try:
        timestamp = os.path.getctime(filepath)
        return datetime.fromtimestamp(timestamp)
    except Exception as e:
        print(f"Erro ao obter data de criação de {filepath}: {e}")
        return None

def scan_directory_for_py_files(directory):
    """Varre o diretório em busca de arquivos .py, calcula hash e data de criação."""
    file_data = []
    unique_files = {}

    pastas_ignoradas = set([
        'venv', '.venv', 'env', '.env', 'lib', 'lib64', 'site-packages', 'dist-packages', 'eggs',
        'pip-wheel-metadata', '__pycache__', 'build', 'dist', 'docs', 'doc', 'etc', 'static',
        'templates', 'media', 'node_modules', '.git', '.svn', '.hg', '.CVS', '.idea', '.vscode',
        'spyder-py3', '.pylint.d', '.mypy_cache', '.pytest_cache', '__pypackages__', 'wheelhouse',
        'htmlcov', '.coverage', 'coverage.xml', '*.egg-info', 'MANIFEST', 'sphinx-build', '_build',
        '_static', '_templates', 'data', 'resources', 'assets', 'out', 'output', 'target', 'log',
        'logs', 'tmp', 'temp', 'cache', 'caches', '.gradle', '.mvn', '.docker', '.vagrant', '.terraform',
        '.ansible', '.terraform.lock.hcl', '.DS_Store', '.Trashes', '$RECYCLE.BIN', 'System Volume Information',
        '._*', '._.Trashes', '._.DS_Store', '.localized', '.AppleDouble',
    ])
    pastas_para_manter = {'test', 'tests', 'testing', 'integration-tests', 'unit-tests', 'functional-tests', 'benchmark', 'benchmarks', 'example', 'examples', 'sample', 'samples', 'notebooks'}
    pastas_ignoradas = pastas_ignoradas.difference(pastas_para_manter)

    for pasta_raiz, subpastas, arquivos in os.walk(directory):
        subpastas[:] = [
            subpasta for subpasta in subpastas
            if subpasta.lower() not in pastas_ignoradas and not subpasta.startswith('.')
        ]
        for arquivo in arquivos:
            if arquivo.endswith(".py"):
                caminho_arquivo = os.path.join(pasta_raiz, arquivo)
                file_hash = calculate_file_hash(caminho_arquivo)
                creation_time = get_original_creation_time(caminho_arquivo)

                if file_hash and creation_time:
                    if file_hash not in unique_files or creation_time > unique_files[file_hash]['creation_time']:
                        unique_files[file_hash] = {'creation_time': creation_time, 'filepath': caminho_arquivo}

    for file_hash_val, file_info in unique_files.items():
        file_data.append({
            'filepath': file_info['filepath'],
            'creation_time': file_info['creation_time'],
            'hash': file_hash_val
        })
    return pd.DataFrame(file_data)

def draw_rounded_rectangle(draw_context, position, size, radius, fill_color):
    """Desenha um retângulo com cantos arredondados."""
    x, y = position
    width, height = size
    rectangle_coords = [
        (x + radius, y),
        (x + width - radius, y),
        (x + width, y + radius),
        (x + width, y + height - radius),
        (x + width - radius, y + height),
        (x + radius, y + height),
        (x, y + height - radius),
        (x, y + radius),
        (x + radius, y)
    ]
    draw_context.polygon(rectangle_coords, fill=fill_color)


def generate_unified_heatmap(df_all_years, output_folder, folder_name_for_file, folder_hash):
    """Gera um heatmap unificado vertical para todos os anos em um único PNG."""

    if df_all_years.empty:
        print("Nenhum arquivo .py encontrado para gerar o heatmap unificado.")
        return

    try:
        windows_font_dir = r"C:\Windows\Fonts" # Caminho padrão das fontes do Windows
        font_month = ImageFont.truetype(os.path.join(windows_font_dir, FONT_NAME + ".ttf"), FONT_SIZE_MONTH)
        font_year = ImageFont.truetype(os.path.join(windows_font_dir, FONT_NAME + ".ttf"), FONT_SIZE_YEAR)
        font_day = ImageFont.truetype(os.path.join(windows_font_dir, FONT_NAME + ".ttf"), FONT_SIZE_DAY)
        font_day_of_week = ImageFont.truetype(os.path.join(windows_font_dir, FONT_DAY_OF_WEEK_NAME + ".ttf"), FONT_SIZE_DAY)
    except IOError:
        font_month = ImageFont.load_default()
        font_year = ImageFont.load_default()
        font_day = ImageFont.load_default()
        font_day_of_week = ImageFont.load_default()
        print("Fontes Arial não encontradas no sistema. Usando fonte padrão.")

    years = sorted(df_all_years['creation_time'].dt.year.unique(), reverse=True)
    num_years = len(years)

    year_block_height = YEAR_LABEL_MARGIN_TOP + YEAR_LABEL_MARGIN_BOTTOM + (7 * (SQUARE_SIZE + SQUARE_PADDING)) + MONTH_LABEL_MARGIN
    image_height_total = MARGIN_TOP + MARGIN_BOTTOM + (num_years * year_block_height) + ((num_years - 1) * YEAR_BLOCK_PADDING) if num_years > 1 else MARGIN_TOP + MARGIN_BOTTOM + year_block_height
    image_width_year = MARGIN_LEFT + MARGIN_RIGHT + YEAR_LABEL_WIDTH + (53 * (SQUARE_SIZE + SQUARE_PADDING))
    image = Image.new('RGB', (image_width_year, image_height_total), IMAGE_BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    current_y_offset = MARGIN_TOP

    for year in years:
        df_year = df_all_years[df_all_years['creation_time'].dt.year == year].copy()
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        num_days = (end_date - start_date).days + 1
        num_weeks = (num_days + start_date.weekday() + (6-end_date.weekday())) // 7

        start_x, start_y_block = MARGIN_LEFT + YEAR_LABEL_WIDTH, current_y_offset + YEAR_LABEL_MARGIN_TOP
        current_x, current_y = start_x, start_y_block

        file_counts = {}
        month_positions = {}

        for _, row in df_year.iterrows():
            creation_date = row['creation_time'].date()
            file_counts[creation_date] = file_counts.get(creation_date, 0) + 1

        year_text = str(year)
        year_text_bbox = draw.textbbox((0, 0), year_text, font=font_year)
        year_text_pos = (MARGIN_LEFT - YEAR_LABEL_WIDTH + (YEAR_LABEL_WIDTH - year_text_bbox[2]) // 2, current_y_offset + YEAR_LABEL_MARGIN_TOP + (year_block_height - YEAR_LABEL_MARGIN_TOP - YEAR_LABEL_MARGIN_BOTTOM) / 2 - year_text_bbox[3] / 2)
        draw.text(year_text_pos, year_text, font=font_year, fill=FONT_COLOR)

        day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for i, day_label in enumerate(day_labels):
            day_text_bbox = draw.textbbox((0, 0), day_label, font=font_day_of_week)
            day_text_pos = (start_x - DAY_LABEL_MARGIN_LEFT - day_text_bbox[2], current_y + i * (SQUARE_SIZE + SQUARE_PADDING) + SQUARE_SIZE / 2 - day_text_bbox[3] / 2)
            draw.text(day_text_pos, day_label, font=font_day_of_week, fill=FONT_COLOR)

        current_date = date(year, 1, 1)
        week_number = 0
        while current_date.year == year:
            day_of_week = current_date.weekday()

            if current_date.day == 1:
                month_positions[current_date.month] = current_x
                month_name = current_date.strftime('%b')
                month_text_bbox = draw.textbbox((0, 0), month_name, font=font_month)
                month_text_pos = (current_x + (SQUARE_SIZE * 7 + SQUARE_PADDING * 6) / 2 - month_text_bbox[2] / 2 , start_y_block - MONTH_LABEL_MARGIN - month_text_bbox[3] )
                draw.text(month_text_pos, month_name, font=font_month, fill=FONT_COLOR)

            if day_of_week == 0:
                line_y = current_y - SQUARE_PADDING / 2
                draw.line([(start_x - DAY_LABEL_MARGIN_LEFT, line_y), (image_width_year - MARGIN_RIGHT, line_y)], fill=GRID_LINE_COLOR, width=GRID_LINE_WIDTH)
            if current_date.weekday() == 6:
                 line_y = current_y + (SQUARE_SIZE + SQUARE_PADDING) * 7 - SQUARE_PADDING / 2
                 draw.line([(start_x - DAY_LABEL_MARGIN_LEFT, line_y), (image_width_year - MARGIN_RIGHT, line_y)], fill=GRID_LINE_COLOR, width=GRID_LINE_WIDTH)

            count = file_counts.get(current_date, 0)
            color_index = min(count, len(HEATMAP_COLORS) - 1) if count > 0 else 0
            fill_color = HEATMAP_COLORS[color_index]

            draw_rounded_rectangle(draw, (current_x, current_y + day_of_week * (SQUARE_SIZE + SQUARE_PADDING)), (SQUARE_SIZE, SQUARE_SIZE), SQUARE_CORNER_RADIUS, fill_color)

            current_date += timedelta(days=1)
            if current_date.weekday() == 0:
                current_x += SQUARE_SIZE + SQUARE_PADDING
                week_number += 1
        draw.line([(start_x - DAY_LABEL_MARGIN_LEFT, current_y + (SQUARE_SIZE + SQUARE_PADDING) * 7 - SQUARE_PADDING / 2), (image_width_year - MARGIN_RIGHT, current_y + (SQUARE_SIZE + SQUARE_PADDING) * 7 - SQUARE_PADDING / 2)], fill=GRID_LINE_COLOR, width=GRID_LINE_WIDTH)

        current_y_offset += year_block_height + YEAR_BLOCK_PADDING


    image_filename = f"heatmap_unified_{folder_name_for_file}-{folder_hash}_all_years.png"
    filepath = os.path.join(output_folder, image_filename)
    image.save(filepath)
    print(f"Heatmap unificado para todos os anos gerado como {filepath}")


if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog
    from datetime import timedelta

    root = tk.Tk()
    root.withdraw()

    directory_path = filedialog.askdirectory(title="Selecione o diretório para varrer arquivos .py")

    if directory_path:
        print(f"Varrendo diretório: {directory_path}")
        all_files_df = scan_directory_for_py_files(directory_path)

        if not all_files_df.empty:
            all_files_df['year'] = all_files_df['creation_time'].dt.year

            base_folder_name = os.path.basename(directory_path)
            directory_hash = hashlib.sha256(directory_path.encode()).hexdigest()[:8]
            output_folder_name = f"{base_folder_name}-{directory_hash}"
            output_folder_path = os.path.join("output_heatmaps_unified_pil", output_folder_name)
            os.makedirs(output_folder_path, exist_ok=True)
            print(f"Heatmap unificado (PIL) será salvo em: {output_folder_path}")

            generate_unified_heatmap(all_files_df, output_folder_path, base_folder_name, directory_hash)

            print(f"Processo completo. Heatmap PNG unificado (PIL) gerado em: {output_folder_path}")
        else:
            print("Nenhum arquivo .py único encontrado no diretório especificado.")
    else:
        print("Nenhum diretório selecionado.")
