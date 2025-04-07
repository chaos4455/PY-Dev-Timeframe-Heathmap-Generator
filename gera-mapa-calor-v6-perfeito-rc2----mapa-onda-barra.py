# generate_activity_charts.py

import os
import hashlib
from datetime import datetime, date, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates # For date formatting on x-axis
import matplotlib.ticker as mticker
import numpy as np
import tkinter as tk
from tkinter import filedialog
import calendar
from collections import defaultdict

# --- Design Constants (Adapted from examples) ---
DARK_BG_COLOR = '#1f1f1f'  # Dark gray background
GRID_COLOR = '#555555'     # Muted grid color
TEXT_COLOR = '#dddddd'     # Light text color
# Colors similar to the "Ocorrências de Segurança" example
COLOR_CREATED = '#ef4444' # Lighter red/coral (Tailwind red-500)
COLOR_MODIFIED = '#b91c1c' # Darker red (Tailwind red-700)
# Or maybe use the colors from the 'Composição' example if preferred:
# COLOR_LOJA_FISICA = '#f97316' # Orange
# COLOR_ONLINE = '#dc2626'     # Red
# COLOR_REVENDEDORES = '#831843' # Maroon
# Let's stick to the 2-color scheme first based on 'Ocorrências'
FONT_NAME = "Arial" # Use Arial or a common sans-serif

# --- File Scanning Functions (Keep as is from previous script) ---
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
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
        lines = 0
        for enc in encodings_to_try:
            try:
                with open(filepath, 'r', encoding=enc) as file:
                    lines = sum(1 for line in file)
                return lines
            except UnicodeDecodeError:
                continue
            except Exception as e_inner:
                 print(f"Erro ao contar linhas em {filepath} com encoding {enc}: {e_inner}")
                 return 0
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
                        existing_mtime = unique_files_by_hash[file_hash].get('modification_time')
                        if isinstance(existing_mtime, datetime) and modification_time <= existing_mtime:
                           is_newer = False

                    if is_newer:
                        lines = count_lines_of_code(caminho_arquivo)
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
                        if isinstance(lines, (int, float)):
                             total_lines += lines

    print(f"Varredura concluída. Total de arquivos escaneados: {scanned_files_count}. Arquivos .py encontrados: {py_files_count}.")
    print(f"Arquivos .py únicos (baseado no hash e mtime): {len(unique_files_by_hash)}.")

    file_data = list(unique_files_by_hash.values())
    return pd.DataFrame(file_data), total_lines, len(unique_files_by_hash)


# --- NEW Plotting Function: Yearly Activity Stacked Bar Chart ---
def create_yearly_activity_chart(
    daily_activity_df, # DataFrame com colunas 'created_count', 'modified_count' e índice de data
    year,
    output_filepath,
    title_prefix="Atividade Diária"
    ):
    """Gera um gráfico de barras empilhadas para a atividade diária de um ano específico."""

    print(f"Gerando gráfico de atividade para o ano {year}: {output_filepath}...")

    if daily_activity_df.empty:
        print(f"  -> Aviso: Nenhum dado de atividade para o ano {year}. Gráfico não gerado.")
        return

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(18, 6)) # Largura maior para acomodar 365 dias
    fig.set_facecolor(DARK_BG_COLOR)
    ax.set_facecolor(DARK_BG_COLOR)

    # --- Data Preparation ---
    dates = daily_activity_df.index
    created_counts = daily_activity_df['created_count']
    modified_counts = daily_activity_df['modified_count']

    # --- Plotting Stacked Bars ---
    # Bar width = 1 para fazer as barras se tocarem visualmente
    bar_width = 1.0

    # Plot 'Created' bars (bottom layer)
    ax.bar(dates, created_counts, width=bar_width, label='Criados', color=COLOR_CREATED, edgecolor=COLOR_CREATED)

    # Plot 'Modified' bars (stacked on top of 'Created')
    ax.bar(dates, modified_counts, bottom=created_counts, width=bar_width, label='Modificados', color=COLOR_MODIFIED, edgecolor=COLOR_MODIFIED)

    # --- Axes Configuration ---
    ax.set_ylabel("Número de Ocorrências", color=TEXT_COLOR, fontsize=11)
    ax.tick_params(axis='y', colors=TEXT_COLOR, labelsize=10)
    # Adjust Y limit based on max total daily activity
    max_daily_total = (created_counts + modified_counts).max()
    ax.set_ylim(0, max_daily_total * 1.15) # Add 15% padding top
    # Ensure Y axis shows integer ticks if counts are integers
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    ax.set_xlabel("Data", color=TEXT_COLOR, fontsize=11, labelpad=10)
    ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=10, rotation=30) # Rotate labels slightly

    # --- X-axis Date Formatting ---
    # Set limits to cover the entire year (or the range of data within the year)
    start_date = pd.Timestamp(f'{year}-01-01')
    end_date = pd.Timestamp(f'{year}-12-31')
    ax.set_xlim(start_date - timedelta(days=5), end_date + timedelta(days=5)) # Add padding

    # Set major ticks for the start of each month
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y')) # Format: Jan 2023

    # Set minor ticks for weeks (optional, can make it busy)
    # ax.xaxis.set_minor_locator(mdates.WeekdayLocator(interval=1))

    # Customize tick label appearance
    plt.setp(ax.get_xticklabels(), ha="right", rotation_mode="anchor")


    # --- Grid ---
    ax.grid(True, axis='y', color=GRID_COLOR, linestyle='--', linewidth=0.6, alpha=0.7)
    ax.grid(False, axis='x') # No vertical grid lines usually needed for this type

    # --- Spines ---
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_edgecolor(GRID_COLOR)
        ax.spines[spine].set_linewidth(0.8)

    # --- Title ---
    ax.set_title(
        f"{title_prefix} - {year}",
        loc='center', fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15
    )

    # --- Legend ---
    legend = ax.legend(facecolor=DARK_BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, fontsize=10)
    legend.get_frame().set_alpha(0.8) # Slightly transparent background

    # --- Final Adjustments & Save ---
    plt.tight_layout(pad=1.5) # Adjust spacing
    try:
        plt.savefig(output_filepath, dpi=150, facecolor=fig.get_facecolor())
        print(f"  -> Gráfico salvo: {output_filepath}")
    except Exception as e:
        print(f"  -> ERRO ao salvar o gráfico {output_filepath}: {e}")
    plt.close(fig) # Close the figure to free memory

# --- Main Execution ---
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

    # --- Aggregation Logic (Same as before) ---
    overall_unique_files = {}
    overall_total_lines = 0
    folder_base_names = []

    for i, dir_path in enumerate(directory_paths):
        folder_base_names.append(os.path.basename(dir_path))
        print(f"\n--- Varrendo pasta {i+1}: {dir_path} ---")
        # Scan returns df_files, total_lines_in_folder, unique_files_in_folder
        df_files, _, _ = scan_directory_for_py_files(dir_path)

        for index, row in df_files.iterrows():
             file_hash = row.get('hash')
             modification_time = row.get('modification_time')
             lines = row.get('lines')

             if not file_hash or not isinstance(modification_time, datetime) or not isinstance(lines, (int, float)):
                 continue

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
        print("\n--- Processando dados para gráficos ---")
        # Ensure datetime types
        if 'creation_time' in unique_files_df_combined.columns:
            unique_files_df_combined['creation_time'] = pd.to_datetime(unique_files_df_combined['creation_time'], errors='coerce')
        if 'modification_time' in unique_files_df_combined.columns:
            unique_files_df_combined['modification_time'] = pd.to_datetime(unique_files_df_combined['modification_time'], errors='coerce')

        # --- Aggregate Data by Day ---
        # Extract Date part
        df = unique_files_df_combined.copy() # Work on a copy
        if 'creation_time' in df.columns:
            df['creation_date'] = df['creation_time'].dt.date
        if 'modification_time' in df.columns:
             df['modification_date'] = df['modification_time'].dt.date

        # Count occurrences per date
        created_counts_daily = df.dropna(subset=['creation_date']).groupby('creation_date').size().rename('created_count')
        modified_counts_daily = df.dropna(subset=['modification_date']).groupby('modification_date').size().rename('modified_count')

        # Combine counts into a single DataFrame, indexed by date
        # Use outer join to include all dates with any activity
        daily_activity = pd.concat([created_counts_daily, modified_counts_daily], axis=1, join='outer')
        daily_activity = daily_activity.fillna(0).astype(int) # Replace NaN with 0
        daily_activity.index = pd.to_datetime(daily_activity.index) # Convert index back to DatetimeIndex

        # Sort by date (important for plotting)
        daily_activity = daily_activity.sort_index()

        if daily_activity.empty:
            print("Nenhuma atividade diária encontrada após agregação.")
        else:
            # --- Create Output Folder ---
            folder_name_for_output = "_".join(folder_base_names)
            folder_hash_combined = hashlib.sha256(folder_name_for_output.encode()).hexdigest()[:8]
            output_folder_name = f"activity_charts_{folder_name_for_output}_{folder_hash_combined}"
            output_folder_path = os.path.join(".", output_folder_name) # Save in current dir subfolder
            os.makedirs(output_folder_path, exist_ok=True)
            print(f"\nGráficos de atividade serão salvos em: {output_folder_path}")

            # --- Generate Chart for Each Year ---
            years_with_data = sorted(daily_activity.index.year.unique())
            print(f"Anos com atividade encontrados: {years_with_data}")

            for year in years_with_data:
                # Filter data for the current year
                yearly_data = daily_activity[daily_activity.index.year == year]

                # Define output filename for this year's chart
                output_filename = f"activity_{year}_{folder_name_for_output}_{folder_hash_combined}.png"
                output_filepath = os.path.join(output_folder_path, output_filename)

                # Call the plotting function
                create_yearly_activity_chart(
                    yearly_data,
                    year,
                    output_filepath,
                    title_prefix=f"Atividade Diária ({', '.join(folder_base_names)})" # Add folder names to title
                )

            print(f"\nProcesso completo. Gráficos PNG de atividade gerados em: {output_folder_path}")

    else:
        print("\nNenhum arquivo .py único encontrado ou dados de tempo inválidos nas pastas especificadas.")