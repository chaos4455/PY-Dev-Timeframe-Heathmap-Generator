# generate_project_time_charts_v2.py

import os
import hashlib
from datetime import datetime, date, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
import tkinter as tk
from tkinter import filedialog
from collections import defaultdict # To store active slots per date
import traceback # For better error reporting

# --- Design Constants - Blue/Ice/Ocean Theme ---
DARK_BG_COLOR = '#1f1f1f'
GRID_COLOR = '#4b5563'
TEXT_COLOR = '#e5e7eb'
COLOR_BAR_FILL = '#3b82f6'
COLOR_AREA_FILL = '#0ea5e9'
COLOR_AREA_EDGE = '#0284c7'
FONT_NAME = "Arial" # Consider 'DejaVu Sans' or others if Arial not found

# --- File Scanning Functions (Simplified) ---
def calculate_file_hash(filepath):
    """Calcula o hash SHA256 de um arquivo."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as file:
            while True:
                chunk = file.read(4096)
                if not chunk: break
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        # print(f"Aviso: Arquivo não encontrado ao calcular hash: {filepath}")
        return None
    except PermissionError:
        # print(f"Aviso: Permissão negada ao calcular hash: {filepath}")
        return None
    except Exception as e:
        # print(f"Erro inesperado ao calcular hash de {filepath}: {e}")
        return None

def get_file_times(filepath):
    """Retorna a data de criação e modificação de um arquivo (datetime objects)."""
    try:
        # Use modification time as the primary indicator, creation time as secondary
        mtime_ts = os.path.getmtime(filepath)
        try:
             ctime_ts = os.path.getctime(filepath)
        except OSError: # On some systems (like Linux often), ctime might be less reliable or same as mtime
             ctime_ts = mtime_ts # Fallback to mtime if ctime fails
        return datetime.fromtimestamp(ctime_ts), datetime.fromtimestamp(mtime_ts)
    except FileNotFoundError:
        # print(f"Aviso: Arquivo não encontrado ao obter datas: {filepath}")
        return None, None
    except PermissionError:
        # print(f"Aviso: Permissão negada ao obter datas: {filepath}")
        return None, None
    except Exception as e:
        # print(f"Erro inesperado ao obter datas de {filepath}: {e}")
        return None, None

# Removed count_lines_of_code function as it's not needed

def scan_directory_for_py_files_simplified(directory):
    """Varre o diretório por .py, obtém hash e datas (sem LOC)."""
    unique_files_by_hash = {} # Store latest file info per hash
    pastas_ignoradas = set(['venv', '.venv', 'env', '.env', 'lib', 'lib64', 'site-packages', 'dist-packages', 'eggs','pip-wheel-metadata', '__pycache__', 'build', 'dist', 'docs', 'doc', 'etc', 'static','templates', 'media', 'node_modules', '.git', '.svn', '.hg', '.CVS', '.idea', '.vscode','spyder-py3', '.pylint.d', '.mypy_cache', '.pytest_cache', '__pypackages__', 'wheelhouse','htmlcov', '.coverage', 'coverage.xml', '*.egg-info', 'MANIFEST', 'sphinx-build', '_build','_static', '_templates', 'data', 'resources', 'assets', 'out', 'output', 'target', 'log','logs', 'tmp', 'temp', 'cache', 'caches', '.gradle', '.mvn', '.docker', '.vagrant', '.terraform','ansible', '.terraform.lock.hcl', '.DS_Store', '.Trashes', '$RECYCLE.BIN', 'System Volume Information','._*', '._.Trashes', '._.DS_Store', '.localized', '.AppleDouble'])
    pastas_para_manter = {'test', 'tests', 'testing', 'integration-tests', 'unit-tests', 'functional-tests', 'benchmark', 'benchmarks', 'example', 'examples', 'sample', 'samples', 'notebooks'}
    pastas_ignoradas = pastas_ignoradas.difference(pastas_para_manter)

    print(f"Iniciando varredura simplificada em: {directory}")
    scanned_files_count = 0
    py_files_count = 0
    skipped_files_time_error = 0
    skipped_files_hash_error = 0

    for pasta_raiz, subpastas, arquivos in os.walk(directory, topdown=True):
        # Filter subdirectories in place
        subpastas[:] = [sp for sp in subpastas if sp.lower() not in pastas_ignoradas and not sp.startswith('.')]

        for arquivo in arquivos:
            scanned_files_count += 1
            if not arquivo.endswith(".py"):
                continue # Skip non-python files early

            py_files_count += 1
            caminho_arquivo = os.path.join(pasta_raiz, arquivo)

            # 1. Get Timestamps
            ctime, mtime = get_file_times(caminho_arquivo)
            if not ctime or not mtime:
                skipped_files_time_error += 1
                continue # Skip if timestamps couldn't be retrieved

            # 2. Get Hash
            file_hash = calculate_file_hash(caminho_arquivo)
            if not file_hash:
                skipped_files_hash_error += 1
                continue # Skip if hash couldn't be calculated

            # 3. Check if newer than existing entry for the same hash
            is_newer = True
            if file_hash in unique_files_by_hash:
                existing_mtime = unique_files_by_hash[file_hash].get('modification_time')
                # Ensure existing_mtime is valid before comparison
                if isinstance(existing_mtime, datetime) and mtime <= existing_mtime:
                    is_newer = False

            if is_newer:
                unique_files_by_hash[file_hash] = {
                    'creation_time': ctime,
                    'modification_time': mtime,
                    'filepath': caminho_arquivo,
                    # 'lines': 0, # No longer storing lines
                    'hash': file_hash
                }

    print(f"Varredura concluída. Total: {scanned_files_count}, Python: {py_files_count}, Únicos: {len(unique_files_by_hash)}")
    if skipped_files_time_error > 0:
        print(f"  -> Aviso: {skipped_files_time_error} arquivos pulados por erro ao obter datas.")
    if skipped_files_hash_error > 0:
         print(f"  -> Aviso: {skipped_files_hash_error} arquivos pulados por erro ao calcular hash.")

    return pd.DataFrame(list(unique_files_by_hash.values()))


# --- Plotting Function: Yearly Project Time Chart (Mostly Unchanged) ---
def create_yearly_time_chart(
    daily_hours_series, year, output_filepath, chart_type='bar',
    title_prefix="Tempo Estimado de Trabalho"):
    """Gera um gráfico de barras ou área para o tempo estimado de projeto por dia."""

    print(f"Gerando gráfico de tempo ({chart_type}) para o ano {year}: {output_filepath}...")

    if daily_hours_series is None or daily_hours_series.empty or daily_hours_series.sum() <= 0:
        print(f"  -> Aviso: Nenhum tempo estimado > 0 para o ano {year}. Gráfico não gerado.")
        return

    try:
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(18, 6))
        fig.set_facecolor(DARK_BG_COLOR)
        ax.set_facecolor(DARK_BG_COLOR)

        # --- Data ---
        # Ensure index is datetime just before plotting
        if not pd.api.types.is_datetime64_any_dtype(daily_hours_series.index):
             daily_hours_series.index = pd.to_datetime(daily_hours_series.index)
        daily_hours_series = daily_hours_series.sort_index() # Ensure sorted

        dates = daily_hours_series.index
        hours_worked = daily_hours_series.values

        # --- Plotting ---
        if chart_type == 'bar':
            ax.bar(dates, hours_worked, width=1.0, label='Horas Estimadas', color=COLOR_BAR_FILL, edgecolor=COLOR_BAR_FILL)
        elif chart_type == 'area':
            ax.fill_between(dates, 0, hours_worked, color=COLOR_AREA_FILL, alpha=0.8, label='Horas Estimadas', linewidth=1.0, edgecolor=COLOR_AREA_EDGE)
        else:
            print(f"  -> Erro: Tipo de gráfico desconhecido '{chart_type}'.")
            plt.close(fig); return

        # --- Axes Configuration ---
        ax.set_ylabel("Horas Trabalhadas (Estimado)", color=TEXT_COLOR, fontsize=11)
        ax.tick_params(axis='y', colors=TEXT_COLOR, labelsize=10)

        max_daily_hours = daily_hours_series.max() if not daily_hours_series.empty else 0
        ax.set_ylim(0, max(max_daily_hours * 1.15, 1.0)) # Ensure ylim is at least 1.0

        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=False, nbins=8, min_n_ticks=4)) # Adjust nbins

        ax.set_xlabel("Data", color=TEXT_COLOR, fontsize=11, labelpad=10)
        ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=10, rotation=30)

        # --- X-axis Date Formatting ---
        start_date = pd.Timestamp(f'{year}-01-01')
        end_date = pd.Timestamp(f'{year}-12-31')
        # Use data limits if available, otherwise fall back to year limits
        min_data_date = dates.min() if not dates.empty else start_date
        max_data_date = dates.max() if not dates.empty else end_date
        ax.set_xlim(min_data_date - timedelta(days=5), max_data_date + timedelta(days=5))

        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b')) # Shorter month format
        # ax.xaxis.set_minor_locator(mdates.WeekdayLocator(interval=2)) # Optional: weekly ticks

        plt.setp(ax.get_xticklabels(), ha="right", rotation_mode="anchor")

        # --- Grid, Spines, Title ---
        ax.grid(True, axis='y', color=GRID_COLOR, linestyle='--', linewidth=0.6, alpha=0.7)
        ax.grid(False, axis='x')
        for spine in ['top', 'right']: ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']: ax.spines[spine].set_edgecolor(GRID_COLOR); ax.spines[spine].set_linewidth(0.8)

        ax.set_title(f"{title_prefix} - {year}", loc='center', fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15)

        # --- Final Adjustments & Save ---
        plt.tight_layout(pad=1.5)
        plt.savefig(output_filepath, dpi=150, facecolor=fig.get_facecolor())
        print(f"  -> Gráfico salvo: {output_filepath}")

    except Exception as e:
        print(f"  -> ERRO CRÍTICO ao gerar gráfico {output_filepath}: {e}")
        # traceback.print_exc() # Uncomment for full error details during debugging
    finally:
        # Ensure plot is closed even if saving fails
        if 'fig' in locals():
            plt.close(fig)


# --- Main Execution ---
if __name__ == "__main__":
    try: # Wrap main execution in try/except for better error catching
        root = tk.Tk(); root.withdraw()
        directory_paths = []
        while True:
            path = filedialog.askdirectory(title=f"Selecione a pasta #{len(directory_paths) + 1} (Cancele para parar)")
            if not path:
                if not directory_paths: print("Nenhuma pasta selecionada. Saindo."); exit()
                else: break
            directory_paths.append(path)

        # --- Aggregation Logic ---
        overall_unique_files_df_list = []
        folder_base_names = []

        print("\n--- Iniciando Varredura Combinada ---")
        for i, dir_path in enumerate(directory_paths):
            folder_base_names.append(os.path.basename(dir_path))
            print(f"--- Varrendo pasta {i+1}: {dir_path} ---")
            # Use the simplified scan function
            df_files = scan_directory_for_py_files_simplified(dir_path)
            if not df_files.empty:
                overall_unique_files_df_list.append(df_files)

        if not overall_unique_files_df_list:
             print("\nNenhum arquivo .py encontrado nas pastas especificadas.")
             exit()

        # Combine dataframes and keep only the latest modification per hash
        combined_df = pd.concat(overall_unique_files_df_list, ignore_index=True)
        # Ensure times are datetime objects *before* finding the latest
        combined_df['creation_time'] = pd.to_datetime(combined_df['creation_time'], errors='coerce')
        combined_df['modification_time'] = pd.to_datetime(combined_df['modification_time'], errors='coerce')
        combined_df = combined_df.dropna(subset=['modification_time', 'creation_time', 'hash']) # Drop rows with invalid data
        # Keep the row with the latest modification_time for each hash
        latest_files_df = combined_df.loc[combined_df.groupby('hash')['modification_time'].idxmax()]

        total_unique_files_combined = len(latest_files_df)
        print(f"--- Varredura Combinada Concluída: {total_unique_files_combined} arquivos .py únicos ---")

        if not latest_files_df.empty:
            print("\n--- Calculando Tempo Estimado por Intervalos de 30 Minutos ---")

            # --- Determine Active 30-Minute Slots ---
            active_slots_by_date = defaultdict(set)

            for index, row in latest_files_df.iterrows():
                # Consider both creation and the *latest* modification time
                timestamps = [row.get('creation_time'), row.get('modification_time')]
                for ts in timestamps:
                    if pd.notna(ts) and isinstance(ts, datetime):
                        event_date = ts.date()
                        try:
                           slot_index = ts.hour * 2 + (0 if ts.minute < 30 else 1)
                           active_slots_by_date[event_date].add(slot_index)
                        except AttributeError:
                           print(f"Aviso: Erro ao processar timestamp {ts} para o arquivo {row.get('filepath')}")


            # --- Calculate Daily Hours ---
            daily_hours_data = {}
            if not active_slots_by_date:
                 print("Aviso: Nenhum slot de tempo ativo encontrado.")
            else:
                min_date = min(active_slots_by_date.keys())
                max_date = max(active_slots_by_date.keys())
                print(f"Período de atividade detectado: {min_date} a {max_date}")

                all_dates = pd.date_range(start=min_date, end=max_date, freq='D')
                daily_hours_list = []
                for current_dt in all_dates:
                    current_date_obj = current_dt.date() # Get date object for lookup
                    num_active_slots = len(active_slots_by_date.get(current_date_obj, set()))
                    estimated_hours = num_active_slots * 0.5
                    daily_hours_list.append({'date': current_dt, 'hours': estimated_hours})

                if not daily_hours_list:
                      print("Nenhum dado de horas diárias para processar.")
                      exit()

                # Convert to Pandas Series
                daily_hours_df = pd.DataFrame(daily_hours_list)
                daily_hours_series = daily_hours_df.set_index('date')['hours']
                daily_hours_series = daily_hours_series.sort_index() # Ensure sorted

                # --- Create Output Folder ---
                folder_name_for_output = "_".join(fn.replace(" ", "_") for fn in folder_base_names) # Sanitize names
                folder_hash_combined = hashlib.sha256(folder_name_for_output.encode()).hexdigest()[:8]
                output_folder_name = f"project_time_{folder_name_for_output}_{folder_hash_combined}"
                output_folder_path = os.path.join(".", output_folder_name)
                os.makedirs(output_folder_path, exist_ok=True)
                print(f"\nGráficos de tempo estimado serão salvos em: {output_folder_path}")

                # --- Generate Charts for Each Year ---
                years_with_data = sorted(daily_hours_series.index.year.unique())
                print(f"Anos com atividade encontrados: {years_with_data}")

                for year in years_with_data:
                    # Filter data for the specific year
                    # Make sure index is datetime before filtering
                    if not pd.api.types.is_datetime64_any_dtype(daily_hours_series.index):
                        daily_hours_series.index = pd.to_datetime(daily_hours_series.index)
                    yearly_data = daily_hours_series[daily_hours_series.index.year == year]

                    if yearly_data.empty or yearly_data.sum() <= 0:
                         print(f"  -> Pulando ano {year}: Sem dados de tempo estimado > 0.")
                         continue # Skip year if no data

                    # Generate Bar Chart
                    output_filename_bar = f"time_bar_{year}_{folder_name_for_output}_{folder_hash_combined}.png"
                    output_filepath_bar = os.path.join(output_folder_path, output_filename_bar)
                    create_yearly_time_chart(
                        yearly_data.copy(), year, output_filepath_bar, chart_type='bar', # Pass a copy
                        title_prefix=f"Tempo Estimado (Barras) - {', '.join(folder_base_names)}"
                    )

                    # Generate Area Chart ("Waves")
                    output_filename_area = f"time_area_{year}_{folder_name_for_output}_{folder_hash_combined}.png"
                    output_filepath_area = os.path.join(output_folder_path, output_filename_area)
                    create_yearly_time_chart(
                        yearly_data.copy(), year, output_filepath_area, chart_type='area', # Pass a copy
                        title_prefix=f"Tempo Estimado (Área) - {', '.join(folder_base_names)}"
                    )

                print(f"\nProcesso completo. Gráficos PNG de tempo estimado gerados em: {output_folder_path}")

        else:
            print("\nNenhum arquivo .py único válido encontrado após combinação e filtragem.")

    except Exception as main_error:
         print("\n--- ERRO INESPERADO NA EXECUÇÃO PRINCIPAL ---")
         print(f"Erro: {main_error}")
         print("\n--- Traceback ---")
         traceback.print_exc()
         print("\nScript interrompido devido a erro.")