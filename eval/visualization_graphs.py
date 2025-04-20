import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import ast
from matplotlib.ticker import MultipleLocator
import matplotlib as mpl
from pathlib import Path
import os
import argparse
import sys

# Set matplotlib parameters for publication quality
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'Arial',
    'font.weight': 'bold',
    'axes.linewidth': 1.5,
    'axes.grid': True,
    'grid.linestyle': '--',
    'grid.alpha': 0.7,
    'xtick.major.width': 1.5,
    'ytick.major.width': 1.5,
    'xtick.major.size': 5,
    'ytick.major.size': 5,
    'axes.titleweight': 'bold',
    'axes.labelweight': 'bold',
    'figure.figsize': (10, 6),
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})
plt.rcParams['pdf.fonttype'] = 42  # TrueType fonts in PDF
plt.rcParams['ps.fonttype'] = 42   # TrueType fonts in PostScript

# Create output directory if it doesn't exist
output_dir = Path('visualization_output')
output_dir.mkdir(exist_ok=True)

# Define a color-blind friendly palette
colors = {
    'english': '#3274A1',    # Blue
    'hindi': '#E1812C',      # Orange
    'roman_hindi': '#3A923A', # Green
    'simple': '#5975A4',     # Light blue
    'complex': '#CC8963',    # Light orange
    'model_colors': plt.cm.Set2
}

def debug_report_structure(report_file):
    """Print the structure of evaluation report to diagnose issues"""
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            
        print(f"Report keys: {list(report_data.keys())}")
        
        # Check if there's a model key or if the report itself is the model data
        if 'queries' in report_data:
            print("Report contains direct 'queries' key (no model nesting)")
            print(f"Number of queries: {len(report_data['queries'])}")
            if report_data['queries']:
                print(f"First query keys: {list(report_data['queries'][0].keys())}")
        else:
            # Check for model-based structure
            for key in report_data:
                if isinstance(report_data[key], dict) and 'queries' in report_data[key]:
                    print(f"Model '{key}' found with {len(report_data[key]['queries'])} queries")
                    if report_data[key]['queries']:
                        print(f"First query keys: {list(report_data[key]['queries'][0].keys())}")
    except Exception as e:
        print(f"Error analyzing report: {e}")

def load_lang_file(lang_file_path):
    """
    Load language information from the lang.txt file
    
    Parameters:
    -----------
    lang_file_path : str
        Path to the lang.txt file
        
    Returns:
    --------
    list
        List of languages for each query
    """
    with open(lang_file_path, 'r', encoding='utf-8') as f:
        languages = [line.strip() for line in f.readlines()]
    
    # Skip the header line
    return languages[1:] if len(languages) > 0 else []

def load_dataset(dataset_path):
    """
    Load the dataset CSV file
    
    Parameters:
    -----------
    dataset_path : str
        Path to the dataset CSV file
        
    Returns:
    --------
    DataFrame
        DataFrame containing the dataset
    """
    return pd.read_csv(dataset_path)

def load_evaluation_reports(report_files, model_names):
    """
    Load evaluation reports from JSON files
    
    Parameters:
    -----------
    report_files : list
        List of paths to evaluation report JSON files
    model_names : list
        List of model names corresponding to each file
        
    Returns:
    --------
    dict
        Dictionary mapping model names to their evaluation data
    """
    reports = {}
    
    for report_file, model_name in zip(report_files, model_names):
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            # Debug the structure
            print(f"Report file: {report_file}")
            print(f"Top-level keys in report: {list(report_data.keys())}")
            
            # Special case for our format with query_scores
            if 'query_scores' in report_data:
                print(f"Found query_scores array in report with {len(report_data['query_scores'])} entries")
                reports[model_name] = report_data
                continue
                
            # Special case for overall_average containing query_scores
            if 'overall_average' in report_data and isinstance(report_data['overall_average'], dict) and 'query_scores' in report_data['overall_average']:
                print(f"Found query_scores array under overall_average with {len(report_data['overall_average']['query_scores'])} entries")
                reports[model_name] = {'query_scores': report_data['overall_average']['query_scores']}
                continue
                
            # Case 1: Report already has model names as keys
            if model_name in report_data:
                reports[model_name] = report_data[model_name]
                print(f"Found model '{model_name}' as key in report")
            
            # Case 2: Report is a flat structure with queries directly
            elif 'queries' in report_data:
                reports[model_name] = report_data
                print(f"Using flat report structure for model '{model_name}'")
            
            # Case 3: Report is nested but model name doesn't match
            else:
                # Just use the first model in the report
                first_model = next(iter(report_data))
                if isinstance(report_data[first_model], dict) and 'queries' in report_data[first_model]:
                    print(f"Warning: Model '{model_name}' not found. Using '{first_model}' from report.")
                    reports[model_name] = report_data[first_model]
                else:
                    # Last resort - create an artificial wrapper
                    print(f"Warning: Unexpected report structure. Creating wrapper for '{model_name}'.")
                    reports[model_name] = {'queries': []}
                    
            # Verify we have queries
            if model_name in reports:
                if 'query_scores' in reports[model_name]:
                    query_scores = reports[model_name]['query_scores']
                    print(f"Loaded {len(query_scores)} query_scores for model '{model_name}'")
                    if query_scores and len(query_scores) > 0:
                        print(f"Sample query_score keys: {list(query_scores[0].keys())}")
                elif 'queries' in reports[model_name]:
                    queries = reports[model_name].get('queries', [])
                    print(f"Loaded {len(queries)} queries for model '{model_name}'")
                    if queries and len(queries) > 0:
                        print(f"Sample query keys: {list(queries[0].keys())}")
            
        except Exception as e:
            print(f"Error loading report {report_file}: {e}")
            reports[model_name] = {'queries': []}
    
    return reports

def extract_language_data(reports, lang_data):
    """
    Extract data grouped by language from evaluation reports and lang.txt
    
    Parameters:
    -----------
    reports : dict
        Dictionary mapping model names to evaluation data
    lang_data : list
        List of languages from lang.txt
        
    Returns:
    --------
    DataFrame
        Processed data organized by model and language
    """
    data = {
        'model': [],
        'language': [],
        'success_rate': [],
        'weighted_score': [],
        'device_score': [],
        'task_score': [],
        'args_score': [],
        'mode_score': [],
        'complexity': []
    }
    
    processed_data = False
    
    # First check if we have the specific report structure with query_scores
    if any('query_scores' in report for report in reports.values()):
        for model_name, report in reports.items():
            if 'query_scores' in report:
                print(f"Found query_scores array for model '{model_name}' with {len(report['query_scores'])} entries")
                query_scores = report['query_scores']
                process_query_scores(data, model_name, query_scores, lang_data)
                processed_data = True
    
    # If we haven't processed any data yet, try using the standard queries array
    if not processed_data:
        print("No query_scores processed, trying standard queries extraction...")
        for model_name, report in reports.items():
            if 'queries' in report:
                queries = report.get('queries', [])
                print(f"Processing {len(queries)} queries for model '{model_name}'")
                
                # Ensure we have language data for all queries
                if len(lang_data) < len(queries):
                    print(f"Warning: Not enough language data entries ({len(lang_data)}) for all queries ({len(queries)})")
                
                for i, query in enumerate(queries):
                    # Make sure query is a dictionary
                    if not isinstance(query, dict):
                        print(f"Warning: Query {i} is not a dictionary: {type(query)}")
                        continue
                        
                    # Get language from lang.txt if available, otherwise use default
                    language = lang_data[i] if i < len(lang_data) else "english"
                    
                    # Standardize language names
                    if language.lower() in ['hindi', 'devnagari', 'devanagari']:
                        language = 'hindi'
                    elif language.lower() in ['rom_hindi', 'romanized hindi', 'roman hindi', 'roman_hindi']:
                        language = 'roman_hindi'
                    else:
                        language = 'english'
                        
                    # Get complexity (with fallback)
                    complexity = query.get('complexity', 'simple')
                    
                    # Check if we have the required metrics
                    if 'success' not in query and 'weighted_score' not in query:
                        print(f"Warning: Query {i} missing success and weighted_score fields")
                        # Try to look for potential renames of these keys
                        alt_keys = [k for k in query.keys() if 'success' in k.lower() or 'score' in k.lower()]
                        if alt_keys:
                            print(f"  Potential alternative keys: {alt_keys}")
                        
                        # Skip this query if we can't find the necessary metrics
                        if not alt_keys:
                            continue
                    
                    # Calculate success metrics (with fallbacks to 0)
                    success = 1 if query.get('success', False) else 0
                    weighted_score = query.get('weighted_score', 0)
                    device_score = query.get('device_score', 0)
                    task_score = query.get('task_score', 0)
                    args_score = query.get('args_score', 0)
                    mode_score = query.get('mode_score', 0)
                    
                    # Append to data
                    data['model'].append(model_name)
                    data['language'].append(language)
                    data['success_rate'].append(success)
                    data['weighted_score'].append(weighted_score)
                    data['device_score'].append(device_score)
                    data['task_score'].append(task_score)
                    data['args_score'].append(args_score)
                    data['mode_score'].append(mode_score)
                    data['complexity'].append(complexity)
                
                processed_data = True
    
    # Check if we have any data
    df = pd.DataFrame(data)
    print(f"Created DataFrame with {len(df)} rows")
    if len(df) == 0:
        print("WARNING: No data extracted for visualization!")
    
    return df

def process_query_scores(data, model_name, query_scores, lang_data):
    """
    Process query_scores array and add data to the data dictionary
    
    Parameters:
    -----------
    data : dict
        The data dictionary to append to
    model_name : str
        The name of the model
    query_scores : list
        List of query score objects
    lang_data : list
        List of languages from lang.txt
    """
    print(f"Processing {len(query_scores)} query scores for model '{model_name}'")
    
    for i, query_data in enumerate(query_scores):
        if i >= len(lang_data):
            print(f"Warning: Not enough language entries (max {len(lang_data)}) for query {i}")
            continue
            
        language = lang_data[i]
        # Standardize language names
        if language.lower() in ['hindi', 'devnagari', 'devanagari']:
            language = 'hindi'
        elif language.lower() in ['rom_hindi', 'romanized hindi', 'roman hindi', 'roman_hindi']:
            language = 'roman_hindi'
        else:
            language = 'english'
        
        # Extract scores from query_data
        query_score = query_data.get('query_score', {})
        
        weighted_score = query_score.get('query_weighted_total', 0)
        device_score = query_score.get('query_device_score', 0)
        task_score = query_score.get('query_task_type_score', 0)
        args_score = query_score.get('query_args_score', 0)
        mode_score = query_score.get('query_mode_score', 0)
        
        # Set success if weighted score is high enough
        success = 1 if weighted_score >= 0.8 else 0
        
        # Determine complexity by query length and number of devices
        devices = query_data.get('devices', [])
        query_text = query_data.get('query', '')
        complexity = 'complex' if len(devices) > 2 or len(query_text.split()) > 10 else 'simple'
        
        # Append to data
        data['model'].append(model_name)
        data['language'].append(language)
        data['success_rate'].append(success)
        data['weighted_score'].append(weighted_score)
        data['device_score'].append(device_score)
        data['task_score'].append(task_score)
        data['args_score'].append(args_score)
        data['mode_score'].append(mode_score)
        data['complexity'].append(complexity)

def plot_success_rate_by_language(data, output_file='success_rate_by_language.pdf'):
    """
    Plot grouped bar chart of success rate by language
    
    Parameters:
    -----------
    data : DataFrame
        Processed evaluation data
    output_file : str
        Output file path
    """
    # Calculate average success rate for each model-language combination
    grouped_data = data.groupby(['model', 'language'])['success_rate'].mean().reset_index()
    
    # Create pivot table for easier plotting
    pivot_data = pd.pivot_table(
        grouped_data, 
        values='success_rate', 
        index=['model'], 
        columns=['language']
    ).reset_index()
    
    # Set up bar positions
    models = pivot_data['model']
    x = np.arange(len(models))
    width = 0.25
    
    # Create bars for each language
    fig, ax = plt.subplots(figsize=(10, 6))
    
    language_order = ['english', 'hindi', 'roman_hindi']
    bars = []
    
    print(f"Plotting success rate graph with data columns: {pivot_data.columns.tolist()}")
    
    for i, lang in enumerate(language_order):
        if lang in pivot_data.columns:
            print(f"Plotting {lang} data: {pivot_data[lang].tolist()}")
            bar = ax.bar(x + (i-1)*width, pivot_data[lang], width, 
                    label=lang.capitalize().replace('_', ' '), 
                    color=colors[lang], edgecolor='black', linewidth=1.5)
            bars.append(bar)
        else:
            print(f"Warning: No data for language '{lang}'")
    
    # Add labels and legend
    ax.set_xlabel('Models', fontweight='bold', fontsize=14)
    ax.set_ylabel('Success Rate', fontweight='bold', fontsize=14)
    ax.set_title('Model Success Rate by Language', fontweight='bold', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha='right', fontweight='bold')
    
    # Only add legend if we have multiple languages
    if len(bars) > 0:
        ax.legend(title='Language', title_fontsize=12, fontsize=10, frameon=True, fancybox=True, framealpha=0.8)
    
    # Add percentage labels on top of bars
    for bar in bars:
        for rect in bar:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2., height + 0.02,
                    f'{height:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_ylim(0, 1.1)  # Set y-axis limit to accommodate labels
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add a subtle background color
    ax.set_facecolor('#f8f8f8')
    
    # Add border around the plot
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)
    
    plt.tight_layout()
    plt.savefig(output_dir / output_file, bbox_inches='tight', dpi=300)
    
    # Also save as PNG for LaTeX use
    plt.savefig(output_dir / output_file.replace('.pdf', '.png'), bbox_inches='tight', dpi=300)
    plt.close()

def plot_weighted_score_by_language(data, output_file='cross_device_performance_by_language.pdf'):
    """
    Plot grouped bar chart of Cross-device Performance Indicator (CDPI) by language
    
    Parameters:
    -----------
    data : DataFrame
        Processed evaluation data
    output_file : str
        Output file path
    """
    # Calculate average weighted score for each model-language combination
    grouped_data = data.groupby(['model', 'language'])['weighted_score'].mean().reset_index()
    
    # Create pivot table for easier plotting
    pivot_data = pd.pivot_table(
        grouped_data, 
        values='weighted_score', 
        index=['model'], 
        columns=['language']
    ).reset_index()
    
    # Set up bar positions
    models = pivot_data['model']
    x = np.arange(len(models))
    width = 0.25
    
    # Create bars for each language
    fig, ax = plt.subplots(figsize=(10, 6))
    
    language_order = ['english', 'hindi', 'roman_hindi']
    bars = []
    
    print(f"Plotting weighted score graph with data columns: {pivot_data.columns.tolist()}")
    
    for i, lang in enumerate(language_order):
        if lang in pivot_data.columns:
            print(f"Plotting {lang} data: {pivot_data[lang].tolist()}")
            bar = ax.bar(x + (i-1)*width, pivot_data[lang], width, 
                    label=lang.capitalize().replace('_', ' '), 
                    color=colors[lang], edgecolor='black', linewidth=1.5)
            bars.append(bar)
        else:
            print(f"Warning: No data for language '{lang}'")
    
    # Add labels and legend
    ax.set_xlabel('Models', fontweight='bold', fontsize=14)
    ax.set_ylabel('Cross-device Performance Indicator (CDPI)', fontweight='bold', fontsize=14)
    ax.set_title('Cross-device Performance Indicator (CDPI) by Language', fontweight='bold', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha='right', fontweight='bold')
    
    # Only add legend if we have multiple languages
    if len(bars) > 0:
        ax.legend(title='Language', title_fontsize=12, fontsize=10, frameon=True, fancybox=True, framealpha=0.8)
    
    # Add score labels on top of bars
    for bar in bars:
        for rect in bar:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2., height + 0.02,
                    f'{height:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_ylim(0, 1.1)  # Set y-axis limit to accommodate labels
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add a subtle background color
    ax.set_facecolor('#f8f8f8')
    
    # Add border around the plot
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)
    
    plt.tight_layout()
    plt.savefig(output_dir / output_file, bbox_inches='tight', dpi=300)
    
    # Also save as PNG for LaTeX use
    plt.savefig(output_dir / output_file.replace('.pdf', '.png'), bbox_inches='tight', dpi=300)
    plt.close()

def plot_parameter_radar_chart(data, output_file='parameter_radar_chart.pdf'):
    """
    Plot radar chart of the 4 parameters that compose the weighted total
    
    Parameters:
    -----------
    data : DataFrame
        Processed evaluation data
    output_file : str
        Output file path
    """
    # Calculate average scores for each model
    radar_data = data.groupby('model')[
        ['device_score', 'task_score', 'args_score', 'mode_score']
    ].mean().reset_index()
    
    # Check if we have data
    if len(radar_data) == 0:
        print("Warning: No data for radar chart. Skipping.")
        return
        
    print(f"Radar chart data:\n{radar_data}")
    
    # Number of variables
    categories = ['Device\nScore', 'Task\nScore', 'Args\nScore', 'Mode\nScore']
    N = len(categories)
    
    # Find minimum and maximum values across all parameters
    min_value = radar_data[['device_score', 'task_score', 'args_score', 'mode_score']].min().min()
    max_value = radar_data[['device_score', 'task_score', 'args_score', 'mode_score']].max().max()
    
    # Round down min to nearest 0.1 and round up max to nearest 0.1 for cleaner limits
    min_value = max(0, np.floor(min_value * 10) / 10)
    max_value = min(1.0, np.ceil(max_value * 10) / 10)
    
    print(f"Setting radar chart range from {min_value} to {max_value}")
    
    # Create angles for each parameter (divide the circle into equal parts)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Close the loop
    
    # Create figure with a polar projection
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, polar=True)
    
    # Set the first axis to be at the top
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    
    # Draw one axis per variable and add labels
    plt.xticks(angles[:-1], categories, fontsize=14, fontweight='bold')
    
    # Set y-axis limit and ticks from min_value to max_value
    value_range = max_value - min_value
    tick_count = 5  # Number of ticks including min and max
    tick_interval = value_range / (tick_count - 1)
    ticks = [min_value + i * tick_interval for i in range(tick_count)]
    
    # Draw the y-axis labels
    ax.set_rlabel_position(0)
    plt.yticks(ticks, [f"{tick:.1f}" for tick in ticks], fontsize=12, color="grey")
    plt.ylim(min_value, max_value)
    
    # Add reference circles with labels for the grid
    for r in ticks:
        if r > min_value and r < max_value:  # Skip the innermost and outermost circles
            circle = plt.Circle((0, 0), r, transform=ax.transData._b, 
                              fill=False, edgecolor='gray', alpha=0.2, linestyle='-')
            ax.add_artist(circle)
    
    # Calculate average across all models for each parameter
    avg_scores = radar_data[['device_score', 'task_score', 'args_score', 'mode_score']].mean()
    avg_values = avg_scores.values.tolist()
    avg_values += avg_values[:1]  # Close the loop
    
    # Plot average line
    ax.plot(angles, avg_values, linewidth=2, linestyle='--', 
            label='Average', color='black', alpha=0.7)
    
    # Plot each model with consistent colors and line styles
    # Define line styles for variation
    line_styles = ['-', '-.', '--', ':']
    markers = ['o', 's', '^', 'D', 'v']
    
    for i, (_, model_data) in enumerate(radar_data.iterrows()):
        model_name = model_data['model']
        values = model_data[['device_score', 'task_score', 'args_score', 'mode_score']].values.tolist()
        values += values[:1]  # Close the loop
        
        # Use consistent color if possible or from color map
        color = colors.get('model_colors')(i/float(len(radar_data)))
        
        # Plot values with variation in line style and markers
        line_style = line_styles[i % len(line_styles)]
        marker = markers[i % len(markers)]
        
        # Plot line
        ax.plot(angles, values, linewidth=3, linestyle=line_style, 
                label=model_name, color=color, marker=marker, markersize=8)
        
        # Fill with transparency
        ax.fill(angles, values, color=color, alpha=0.15)
    
    # Move legend outside the plot
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), 
              fontsize=12, frameon=True, fancybox=True, framealpha=0.8, ncol=3)
    
    # Add background grid with improved visibility
    ax.grid(True, linestyle='--', alpha=0.5, color='gray')
    
    # Add title
    plt.title('Model Performance Across Parameters', size=18, fontweight='bold', pad=20)
    
    # Add subtle background
    ax.set_facecolor('#f9f9f9')
    
    plt.tight_layout()
    plt.savefig(output_dir / output_file, bbox_inches='tight', dpi=300)
    
    # Also save as PNG for LaTeX use
    plt.savefig(output_dir / output_file.replace('.pdf', '.png'), bbox_inches='tight', dpi=300)
    plt.close()

def plot_complexity_scores(data, output_file='complexity_scores.pdf'):
    """
    Plot horizontal grouped bar chart for all models based on score on simple and complex queries
    
    Parameters:
    -----------
    data : DataFrame
        Processed evaluation data
    output_file : str
        Output file path
    """
    # Check if we have complexity data
    if 'complexity' not in data.columns or data['complexity'].nunique() <= 1:
        print("Warning: No complexity data or only one complexity level. Skipping complexity chart.")
        return
        
    # Calculate average weighted score for each model-complexity combination
    grouped_data = data.groupby(['model', 'complexity'])['weighted_score'].mean().reset_index()
    
    # Create pivot table for easier plotting
    pivot_data = pd.pivot_table(
        grouped_data, 
        values='weighted_score', 
        index=['model'], 
        columns=['complexity']
    ).reset_index()
    
    print(f"Complexity data columns: {pivot_data.columns.tolist()}")
    
    # Sort by average score across both complexities
    if 'simple' in pivot_data.columns and 'complex' in pivot_data.columns:
        pivot_data['avg_score'] = (pivot_data['simple'] + pivot_data['complex']) / 2
        pivot_data = pivot_data.sort_values('avg_score', ascending=False)
        pivot_data = pivot_data.drop('avg_score', axis=1)
    
    # Create horizontal bar chart
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Model names and positions
    models = pivot_data['model']
    y = np.arange(len(models))
    width = 0.35
    
    # Plot bars
    if 'simple' in pivot_data.columns:
        print(f"Plotting simple data: {pivot_data['simple'].tolist()}")
        simple_bars = ax.barh(y - width/2, pivot_data['simple'], width, 
                              label='Simple Queries', color=colors['simple'], 
                              edgecolor='black', linewidth=1.5)
    
    if 'complex' in pivot_data.columns:
        print(f"Plotting complex data: {pivot_data['complex'].tolist()}")
        complex_bars = ax.barh(y + width/2, pivot_data['complex'], width, 
                               label='Complex Queries', color=colors['complex'], 
                               edgecolor='black', linewidth=1.5)
    
    # Add labels and title
    ax.set_xlabel('Average Cross-device Performance Indicator (CDPI)', fontweight='bold', fontsize=14)
    ax.set_ylabel('Models', fontweight='bold', fontsize=14)
    ax.set_title('Model Performance on Simple vs Complex Queries', fontweight='bold', fontsize=16)
    ax.set_yticks(y)
    ax.set_yticklabels(models, fontweight='bold')
    
    # Only add legend if we have both complexity types
    if 'simple' in pivot_data.columns and 'complex' in pivot_data.columns:
        ax.legend(fontsize=12, frameon=True, fancybox=True, framealpha=0.8)
    
    # Add score labels on bars
    if 'simple' in pivot_data.columns:
        for i, bar in enumerate(simple_bars):
            width = bar.get_width()
            ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                    f'{width:.2f}', va='center', fontsize=10, fontweight='bold')
    
    if 'complex' in pivot_data.columns:
        for i, bar in enumerate(complex_bars):
            width = bar.get_width()
            ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                    f'{width:.2f}', va='center', fontsize=10, fontweight='bold')
    
    ax.set_xlim(0, 1.1)  # Set x-axis limit to accommodate labels
    ax.xaxis.set_major_locator(MultipleLocator(0.1))
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add a subtle background color
    ax.set_facecolor('#f8f8f8')
    
    # Add border around the plot
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)
    
    plt.tight_layout()
    plt.savefig(output_dir / output_file, bbox_inches='tight', dpi=300)
    
    # Also save as PNG for LaTeX use
    plt.savefig(output_dir / output_file.replace('.pdf', '.png'), bbox_inches='tight', dpi=300)
    plt.close()

def plot_complexity_success_rates(data, output_file='complexity_success_rates.pdf'):
    """
    Plot horizontal grouped bar chart for all models based on success rate on simple and complex queries
    
    Parameters:
    -----------
    data : DataFrame
        Processed evaluation data
    output_file : str
        Output file path
    """
    # Check if we have complexity data
    if 'complexity' not in data.columns or data['complexity'].nunique() <= 1:
        print("Warning: No complexity data or only one complexity level. Skipping complexity success rates chart.")
        return
        
    # Calculate average success rate for each model-complexity combination
    grouped_data = data.groupby(['model', 'complexity'])['success_rate'].mean().reset_index()
    
    # Create pivot table for easier plotting
    pivot_data = pd.pivot_table(
        grouped_data, 
        values='success_rate', 
        index=['model'], 
        columns=['complexity']
    ).reset_index()
    
    print(f"Complexity success rates data columns: {pivot_data.columns.tolist()}")
    
    # Sort by average success rate across both complexities
    if 'simple' in pivot_data.columns and 'complex' in pivot_data.columns:
        pivot_data['avg_success'] = (pivot_data['simple'] + pivot_data['complex']) / 2
        pivot_data = pivot_data.sort_values('avg_success', ascending=False)
        pivot_data = pivot_data.drop('avg_success', axis=1)
    
    # Create horizontal bar chart
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Model names and positions
    models = pivot_data['model']
    y = np.arange(len(models))
    width = 0.35
    
    # Plot bars
    if 'simple' in pivot_data.columns:
        print(f"Plotting simple success rates: {pivot_data['simple'].tolist()}")
        simple_bars = ax.barh(y - width/2, pivot_data['simple'], width, 
                              label='Simple Queries', color=colors['simple'], 
                              edgecolor='black', linewidth=1.5)
    
    if 'complex' in pivot_data.columns:
        print(f"Plotting complex success rates: {pivot_data['complex'].tolist()}")
        complex_bars = ax.barh(y + width/2, pivot_data['complex'], width, 
                               label='Complex Queries', color=colors['complex'], 
                               edgecolor='black', linewidth=1.5)
    
    # Add labels and title
    ax.set_xlabel('Average Success Rate', fontweight='bold', fontsize=14)
    ax.set_ylabel('Models', fontweight='bold', fontsize=14)
    ax.set_title('Model Success Rate on Simple vs Complex Queries', fontweight='bold', fontsize=16)
    ax.set_yticks(y)
    ax.set_yticklabels(models, fontweight='bold')
    
    # Only add legend if we have both complexity types
    if 'simple' in pivot_data.columns and 'complex' in pivot_data.columns:
        ax.legend(fontsize=12, frameon=True, fancybox=True, framealpha=0.8)
    
    # Add success rate labels on bars
    if 'simple' in pivot_data.columns:
        for i, bar in enumerate(simple_bars):
            width = bar.get_width()
            ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                    f'{width:.2f}', va='center', fontsize=10, fontweight='bold')
    
    if 'complex' in pivot_data.columns:
        for i, bar in enumerate(complex_bars):
            width = bar.get_width()
            ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                    f'{width:.2f}', va='center', fontsize=10, fontweight='bold')
    
    ax.set_xlim(0, 1.1)  # Set x-axis limit to accommodate labels
    ax.xaxis.set_major_locator(MultipleLocator(0.1))
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add a subtle background color
    ax.set_facecolor('#f8f8f8')
    
    # Add border around the plot
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)
    
    plt.tight_layout()
    plt.savefig(output_dir / output_file, bbox_inches='tight', dpi=300)
    
    # Also save as PNG for LaTeX use
    plt.savefig(output_dir / output_file.replace('.pdf', '.png'), bbox_inches='tight', dpi=300)
    plt.close()

# Then modify the generate_all_visualizations function to include this new plot
def generate_all_visualizations(report_files, model_names, lang_file='lang.txt'):
    """
    Generate all visualizations based on evaluation reports
    
    Parameters:
    -----------
    report_files : list
        List of paths to evaluation report JSON files
    model_names : list
        List of model names corresponding to each file
    lang_file : str
        Path to the lang.txt file containing language information
    """
    # Add debug code to check files exist
    for file in [lang_file] + report_files:
        if os.path.exists(file):
            file_size = os.path.getsize(file)
            print(f"File '{file}' exists ({file_size} bytes)")
        else:
            print(f"WARNING: File '{file}' does not exist!")
    
    # Load language data
    lang_data = load_lang_file(lang_file)
    print(f"Loaded {len(lang_data)} language entries from {lang_file}")
    
    # Debug report structure before loading
    for report_file in report_files:
        if os.path.exists(report_file):
            debug_report_structure(report_file)
    
    # Load evaluation reports
    reports = load_evaluation_reports(report_files, model_names)
    
    # Check if we have any reports loaded
    if not reports:
        print("ERROR: No reports were loaded. Check file paths and model names.")
        return
    
    # Extract data with language information from lang.txt
    data = extract_language_data(reports, lang_data)
    
    # Check if we have data before generating visualizations
    if len(data) == 0:
        print("ERROR: No data extracted from reports. Visualizations will be empty.")
        print("Try checking the report file structure against the expected format.")
        return
    
    # Print some stats about the data to help diagnose
    print("\nData statistics:")
    for model in data['model'].unique():
        model_data = data[data['model'] == model]
        print(f"Model '{model}': {len(model_data)} data points")
        for lang in model_data['language'].unique():
            lang_data = model_data[model_data['language'] == lang]
            print(f"  Language '{lang}': {len(lang_data)} data points")
            print(f"    Success rate: {lang_data['success_rate'].mean():.2f}")
            print(f"    Cross-device Performance Indicator (CDPI): {lang_data['weighted_score'].mean():.2f}")
        
        # Add complexity stats
        if 'complexity' in data.columns:
            for complexity in model_data['complexity'].unique():
                complexity_data = model_data[model_data['complexity'] == complexity]
                print(f"  Complexity '{complexity}': {len(complexity_data)} data points")
                print(f"    Success rate: {complexity_data['success_rate'].mean():.2f}")
                print(f"    Cross-device Performance Indicator (CDPI): {complexity_data['weighted_score'].mean():.2f}")
    
    # Generate visualizations
    plot_success_rate_by_language(data)
    plot_weighted_score_by_language(data)
    plot_parameter_radar_chart(data)
    plot_complexity_scores(data)
    plot_complexity_success_rates(data)  # Add the new visualization
    
    print(f"Visualizations generated successfully in {output_dir}")
    print(f"Files saved in both PDF and PNG formats for LaTeX compatibility")
    
    # Print LaTeX code for including the figures
    print("\nLaTeX code for including figures in your document:\n")
    
    print(r"\begin{figure}[htbp]")
    print(r"    \centering")
    print(r"    \includegraphics[width=0.8\textwidth]{visualization_output/success_rate_by_language.pdf}")
    print(r"    \caption{Model Success Rate by Language}")
    print(r"    \label{fig:success_rate}")
    print(r"\end{figure}")
    
    print("\n")
    
    print(r"\begin{figure}[htbp]")
    print(r"    \centering")
    print(r"    \includegraphics[width=0.8\textwidth]{visualization_output/cross_device_performance_by_language.pdf}")
    print(r"    \caption{Cross-device Performance Indicator (CDPI) by Language}")
    print(r"    \label{fig:cdpi_by_language}")
    print(r"\end{figure}")
    
    print("\n")
    
    print(r"\begin{figure}[htbp]")
    print(r"    \centering")
    print(r"    \includegraphics[width=0.7\textwidth]{visualization_output/parameter_radar_chart.pdf}")
    print(r"    \caption{Model Performance Across Parameters}")
    print(r"    \label{fig:radar_chart}")
    print(r"\end{figure}")
    
    print("\n")
    
    print(r"\begin{figure}[htbp]")
    print(r"    \centering")
    print(r"    \includegraphics[width=0.8\textwidth]{visualization_output/complexity_scores.pdf}")
    print(r"    \caption{Model Performance (CDPI) on Simple vs Complex Queries}")
    print(r"    \label{fig:complexity_scores}")
    print(r"\end{figure}")
    
    print("\n")
    
    print(r"\begin{figure}[htbp]")
    print(r"    \centering")
    print(r"    \includegraphics[width=0.8\textwidth]{visualization_output/complexity_success_rates.pdf}")
    print(r"    \caption{Model Success Rate on Simple vs Complex Queries}")
    print(r"    \label{fig:complexity_success_rates}")
    print(r"\end{figure}")# Example usage
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Generate visualizations from evaluation reports')
    parser.add_argument('--reports', nargs='+', help='Paths to evaluation report files (default: evaluation_report.json)')
    parser.add_argument('--models', nargs='+', help='Model names to use (default: auto-detect from reports)')
    parser.add_argument('--lang', default='lang.txt', help='Path to language file (default: lang.txt)')
    args = parser.parse_args()
    
    # Use provided reports or default to evaluation_report.json
    report_files = args.reports if args.reports else ['evaluation_report.json']
    
    # Check if all specified reports exist
    missing_files = [f for f in report_files if not os.path.exists(f)]
    if missing_files:
        print(f"Error: The following report files were not found: {', '.join(missing_files)}")
        sys.exit(1)
    
    # Check if no valid reports were found
    if not report_files:
        print("Error: No valid report files specified or found")
        sys.exit(1)
    
    # Initialize model_names
    model_names = args.models
    
    # If no model names are provided, try to auto-detect from the first report
    if not model_names:
        try:
            with open(report_files[0], 'r', encoding='utf-8') as f:
                report_data = json.load(f)
                
                # Check for specific format with query_scores
                if 'query_scores' in report_data:
                    print(f"Found query_scores at top level in {report_files[0]}, using special format")
                    model_names = ['Model']  # Use a generic model name
                elif 'overall_average' in report_data and 'query_scores' in report_data.get('overall_average', {}):
                    print(f"Found query_scores under overall_average in {report_files[0]}, using special format")
                    model_names = ['Model']
                # Check if report has model keys or is a flat structure
                elif 'queries' in report_data:
                    # Flat structure - use generic model name
                    model_names = ['Default Model']
                    print(f"Using flat report structure with model name: {model_names[0]}")
                else:
                    # Report has model keys
                    model_names = list(report_data.keys())
                    print(f"Detected model names in report: {model_names}")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error processing {report_files[0]}: {str(e)}")
            model_names = ['Unknown Model']
    else:
        print(f"Using provided model names: {model_names}")
    
    # Generate visualizations
    generate_all_visualizations(report_files, model_names, lang_file=args.lang)
    
    print("\nVisualization generation complete. Files saved to 'visualization_output/' directory.") 