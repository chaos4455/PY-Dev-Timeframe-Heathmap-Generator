# generate_loc_charts.py

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

# --- Design Constants (Same as before) ---
DARK_BG_COLOR = '#1f1f1f'
GRID_COLOR = '#555555'
TEXT_COLOR = '#dddddd'
COLOR_CREATED_LOC = '#ef4444' # Lighter red/coral for LOC in newly created files
COLOR_MODIFIED_LOC = '#b91c1c' # Darker red for LOC in modified files
FONT_NAME = "Arial"

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
        # print(f"Erro ao calcular hash de {filepath}: {e}") # Optional: reduce noise
        return None

def get_file_times(filepath):
    """Retorna a data de criação e modificação de um arquivo (datetime objects)."""
    try:
        creation_timestamp = os.path.getctime(filepath)
        modification_timestamp = os.path.getmtime(filepath)
        return datetime.fromtimestamp(creation_timestamp), datetime.fromtimestamp(modification_timestamp)
    except Exception as e:
        # print(f"Erro ao obter datas de {filepath}: {e}") # Optional: reduce noise
        return None, None

def count_lines_of_code(filepath):
    """Conta o número de linhas de código em um arquivo."""
    try:
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
        lines = 0
        read_success = False
        for enc in encodings_to_try:
            try:
                with open(filepath, 'r', encoding=enc) as file:
                    lines = sum(1 for line in file)
                read_success = True
                break # Stop on first success
            except UnicodeDecodeError:
                continue
            except Exception as e_inner:
                 # print(f"Erro ao contar linhas em {filepath} com encoding {enc}: {e_inner}") # Optional
                 return 0 # Return 0 on read error

        if not read_success:
            try:
                # Last resort with ignoring errors
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                    lines = sum(1 for line in file)
                read_success = True
            except Exception as e_final:
                # print(f"Erro final ao contar linhas em {filepath}: {e_final}") # Optional
                return 0

        return lines if read_success else 0

    except Exception as e:
        # print(f"Erro geral ao processar {filepath} para contagem de linhas: {e}") # Optional
        return 0


def scan_directory_for_py_files(directory):
    """Varre o diretório em busca de arquivos .py, calcula hash, datas e LOC."""
    # (Implementation is identical to the previous version, including ignored folders)
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
                        # Ensure lines is numeric before proceeding
                        if not isinstance(lines, (int, float)):
                           lines = 0 # Default to 0 if count failed

                        if file_hash in unique_files_by_hash:
                            existing_lines = unique_files_by_hash[file_hash].get('lines')
                            if isinstance(existing_lines, (int, float)):
                                total_lines -= existing_lines # Subtract old LOC count

                        unique_files_by_hash[file_hash] = {
                            'creation_time': creation_time,
                            'modification_time': modification_time,
                            'filepath': caminho_arquivo,
                            'lines': lines, # Store the calculated LOC
                            'hash': file_hash
                        }
                        total_lines += lines # Add new LOC count

    # print(f"Varredura concluída. Total de arquivos escaneados: {scanned_files_count}. Arquivos .py encontrados: {py_files_count}.")
    # print(f"Arquivos .py únicos (baseado no hash e mtime): {len(unique_files_by_hash)}.")
    # print(f"Total de linhas de código (aproximado): {total_lines}") # Optional: Print total LOC sum

    file_data = list(unique_files_by_hash.values())
    return pd.DataFrame(file_data), total_lines, len(unique_files_by_hash)


# --- Modified Plotting Function: Yearly LOC Stacked Bar Chart ---
def create_yearly_loc_chart(
    daily_loc_df, # DataFrame com colunas 'created_loc', 'modified_loc' e índice de data
    year,
    output_filepath,
    title_prefix="Atividade Diária (LOC)"
    ):
    """Gera um gráfico de barras empilhadas para a SOMA de linhas de código por dia."""

    print(f"Gerando gráfico de LOC para o ano {year}: {output_filepath}...")

    if daily_loc_df.empty or daily_loc_df.sum().sum() == 0 : # Check if empty or all zeros
        print(f"  -> Aviso: Nenhum dado de LOC para o ano {year}. Gráfico não gerado.")
        return

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(18, 6))
    fig.set_facecolor(DARK_BG_COLOR)
    ax.set_facecolor(DARK_BG_COLOR)

    # --- Data Preparation ---
    dates = daily_loc_df.index
    created_loc = daily_loc_df['created_loc']
    modified_loc = daily_loc_df['modified_loc']

    # --- Plotting Stacked Bars ---
    bar_width = 1.0

    # Plot 'Created LOC' bars (bottom layer)
    # Represents the sum of lines from files *created* on this day
    ax.bar(dates, created_loc, width=bar_width, label='LOC Criados', color=COLOR_CREATED_LOC, edgecolor=COLOR_CREATED_LOC)

    # Plot 'Modified LOC' bars (stacked on top of 'Created LOC')
    # Represents the sum of lines from the *latest version* of files *modified* on this day
    ax.bar(dates, modified_loc, bottom=created_loc, width=bar_width, label='LOC Modificados', color=COLOR_MODIFIED_LOC, edgecolor=COLOR_MODIFIED_LOC)

    # --- Axes Configuration ---
    ax.set_ylabel("Linhas de Código (LOC)", color=TEXT_COLOR, fontsize=11) # Updated Y label
    ax.tick_params(axis='y', colors=TEXT_COLOR, labelsize=10)

    max_daily_total_loc = (created_loc + modified_loc).max()
    ax.set_ylim(0, max_daily_total_loc * 1.15 if max_daily_total_loc > 0 else 10) # Ensure ylim is positive
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    # Optional: Format Y-axis labels for large numbers (e.g., thousands 'k')
    ax.yaxis.set_major_formatter(mticker.EngFormatter())


    ax.set_xlabel("Data", color=TEXT_COLOR, fontsize=11, labelpad=10)
    ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=10, rotation=30)

    # --- X-axis Date Formatting (Same as before) ---
    start_date = pd.Timestamp(f'{year}-01-01')
    end_date = pd.Timestamp(f'{year}-12-31')
    ax.set_xlim(start_date - timedelta(days=5), end_date + timedelta(days=5))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.setp(ax.get_xticklabels(), ha="right", rotation_mode="anchor")

    # --- Grid, Spines, Title (Styling mostly same as before) ---
    ax.grid(True, axis='y', color=GRID_COLOR, linestyle='--', linewidth=0.6, alpha=0.7)
    ax.grid(False, axis='x')
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_edgecolor(GRID_COLOR)
        ax.spines[spine].set_linewidth(0.8)

    ax.set_title(
        f"{title_prefix} - {year}", # Updated Title Prefix
        loc='center', fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15
    )

    # --- Legend (Updated labels) ---
    legend = ax.legend(facecolor=DARK_BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, fontsize=10)
    legend.get_frame().set_alpha(0.8)

    # --- Final Adjustments & Save ---
    plt.tight_layout(pad=1.5)
    try:
        plt.savefig(output_filepath, dpi=150, facecolor=fig.get_facecolor())
        print(f"  -> Gráfico salvo: {output_filepath}")
    except Exception as e:
        print(f"  -> ERRO ao salvar o gráfico {output_filepath}: {e}")
    plt.close(fig)

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

    # --- Aggregation Logic (Same folder scanning) ---
    overall_unique_files = {}
    overall_total_lines = 0
    folder_base_names = []

    for i, dir_path in enumerate(directory_paths):
        folder_base_names.append(os.path.basename(dir_path))
        print(f"\n--- Varrendo pasta {i+1}: {dir_path} ---")
        # Scan returns df_files, total_lines_in_folder, unique_files_in_folder
        df_files, folder_lines, folder_unique_count = scan_directory_for_py_files(dir_path)
        print(f"    Arquivos .py únicos na pasta: {folder_unique_count}, Linhas: {folder_lines}")


        for index, row in df_files.iterrows():
             file_hash = row.get('hash')
             modification_time = row.get('modification_time')
             lines = row.get('lines') # Get the LOC for this file

             # Basic validation
             if not file_hash or not isinstance(modification_time, datetime) or not isinstance(lines, (int, float)):
                 # print(f"Aviso: Dados inválidos ou ausentes para linha {index} em {dir_path}. Pulando.")
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
                            overall_total_lines -= existing_lines # Subtract old LOC

                  overall_unique_files[file_hash] = row.to_dict()
                  overall_total_lines += lines # Add new LOC

    unique_files_df_combined = pd.DataFrame(list(overall_unique_files.values()))
    total_unique_files_combined = len(unique_files_df_combined)

    if not unique_files_df_combined.empty:
        print("\n--- Processando dados para gráficos de LOC ---")
        # Ensure datetime types
        if 'creation_time' in unique_files_df_combined.columns:
            unique_files_df_combined['creation_time'] = pd.to_datetime(unique_files_df_combined['creation_time'], errors='coerce')
        if 'modification_time' in unique_files_df_combined.columns:
            unique_files_df_combined['modification_time'] = pd.to_datetime(unique_files_df_combined['modification_time'], errors='coerce')
        # Ensure lines is numeric, coerce errors to NaN then fill with 0
        if 'lines' in unique_files_df_combined.columns:
            unique_files_df_combined['lines'] = pd.to_numeric(unique_files_df_combined['lines'], errors='coerce').fillna(0).astype(int)
        else:
             print("Aviso: Coluna 'lines' não encontrada no DataFrame combinado.")
             unique_files_df_combined['lines'] = 0 # Add a default lines column if missing


        # --- Aggregate Lines of Code by Day ---
        df_loc = unique_files_df_combined.copy()
        if 'creation_time' in df_loc.columns:
            df_loc['creation_date'] = df_loc['creation_time'].dt.date
        if 'modification_time' in df_loc.columns:
             df_loc['modification_date'] = df_loc['modification_time'].dt.date

        # Sum 'lines' based on creation date
        created_loc_daily = df_loc.dropna(subset=['creation_date']).groupby('creation_date')['lines'].sum().rename('created_loc')

        # Sum 'lines' based on modification date
        # IMPORTANT: This sums the *total current lines* of files modified that day, not the delta.
        modified_loc_daily = df_loc.dropna(subset=['modification_date']).groupby('modification_date')['lines'].sum().rename('modified_loc')

        # Combine LOC counts into a single DataFrame
        daily_activity_loc = pd.concat([created_loc_daily, modified_loc_daily], axis=1, join='outer')
        daily_activity_loc = daily_activity_loc.fillna(0).astype(int) # Replace NaN with 0 LOC
        daily_activity_loc.index = pd.to_datetime(daily_activity_loc.index) # Convert index back to DatetimeIndex

        # Sort by date
        daily_activity_loc = daily_activity_loc.sort_index()

        # Filter out potential modification counts for the *same day* as creation to avoid double counting LOC sum
        # If a file is created and modified on the same day, attribute its LOC only to 'created_loc' for that day.
        common_index = daily_activity_loc.index.intersection(
            df_loc[df_loc['creation_date'] == df_loc['modification_date']]['creation_date'].unique()
        )
        if not common_index.empty:
            # Get files created and modified on the same day
            same_day_files = df_loc[df_loc['creation_date'] == df_loc['modification_date']]
            # Calculate the LOC sum for these files grouped by that day
            same_day_loc_sum = same_day_files.groupby('creation_date')['lines'].sum()
            # Subtract this sum from the 'modified_loc' for those specific days
            daily_activity_loc.loc[same_day_loc_sum.index, 'modified_loc'] -= same_day_loc_sum
            # Ensure modified_loc doesn't go below zero
            daily_activity_loc['modified_loc'] = daily_activity_loc['modified_loc'].clip(lower=0)


        if daily_activity_loc.empty or daily_activity_loc.sum().sum() == 0:
            print("Nenhuma atividade de LOC diária encontrada após agregação.")
        else:
            # --- Create Output Folder ---
            folder_name_for_output = "_".join(folder_base_names)
            folder_hash_combined = hashlib.sha256(folder_name_for_output.encode()).hexdigest()[:8]
            output_folder_name = f"loc_charts_{folder_name_for_output}_{folder_hash_combined}" # Changed folder name
            output_folder_path = os.path.join(".", output_folder_name)
            os.makedirs(output_folder_path, exist_ok=True)
            print(f"\nGráficos de atividade de LOC serão salvos em: {output_folder_path}")
            print(f"Total de arquivos .py únicos combinados: {total_unique_files_combined}")
            print(f"Total de linhas de código nesses arquivos: {overall_total_lines:,}".replace(",", "."))


            # --- Generate Chart for Each Year ---
            years_with_data = sorted(daily_activity_loc.index.year.unique())
            print(f"Anos com atividade de LOC encontrados: {years_with_data}")

            for year in years_with_data:
                yearly_data_loc = daily_activity_loc[daily_activity_loc.index.year == year]

                # Define output filename for this year's LOC chart
                output_filename = f"loc_activity_{year}_{folder_name_for_output}_{folder_hash_combined}.png" # Changed file name prefix
                output_filepath = os.path.join(output_folder_path, output_filename)

                # Call the updated plotting function
                create_yearly_loc_chart(
                    yearly_data_loc,
                    year,
                    output_filepath,
                    title_prefix=f"Atividade Diária (LOC) - {', '.join(folder_base_names)}" # Add folder names to title
                )

            print(f"\nProcesso completo. Gráficos PNG de atividade de LOC gerados em: {output_folder_path}")

    else:
        print("\nNenhum arquivo .py único encontrado ou dados de tempo inválidos nas pastas especificadas.")