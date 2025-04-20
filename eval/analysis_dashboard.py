import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns

def load_data(file_path):
    """Load JSON data from the given file path"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def extract_device_metrics(data):
    """Extract device-specific metrics from the data"""
    device_metrics = defaultdict(lambda: {
        'total': 0,
        'device_score': 0,
        'task_type_score': 0,
        'mode_score': 0, 
        'args_score': 0,
        'weighted_total': 0,
        'success_rate': 0,
        'failure_count': 0
    })
    
    for query in data['query_scores']:
        for device in query['devices']:
            device_name = device['actual']['device']
            metrics = device_metrics[device_name]
            metrics['total'] += 1
            metrics['device_score'] += device['score']['device_score']
            metrics['task_type_score'] += device['score']['task_type_score']
            metrics['mode_score'] += device['score']['mode_score']
            metrics['args_score'] += device['score']['args_score']
            metrics['weighted_total'] += device['score']['weighted_total']
            
            # Track success/failure
            if device['score']['weighted_total'] == 1.0:
                metrics['success_rate'] += 1
            else:
                metrics['failure_count'] += 1
    
    # Convert to averages and percentages
    for device in device_metrics:
        total = device_metrics[device]['total']
        for metric in ['device_score', 'task_type_score', 'mode_score', 'args_score', 'weighted_total']:
            device_metrics[device][metric] /= total
        
        device_metrics[device]['success_rate'] = (device_metrics[device]['success_rate'] / total) * 100
            
    return dict(device_metrics)

def analyze_language_performance(data):
    """Analyze performance based on language (Hindi vs English)"""
    hindi_queries = []
    english_queries = []
    
    hindi_components = {
        'device_score': [],
        'task_type_score': [],
        'mode_score': [],
        'args_score': []
    }
    
    english_components = {
        'device_score': [],
        'task_type_score': [],
        'mode_score': [],
        'args_score': []
    }
    
    for query in data['query_scores']:
        # Check if Hindi query
        is_hindi = any(ord('\u0900') <= ord(c) <= ord('\u097F') for c in query['query'])
        
        # Add the query's weighted score to the appropriate list
        if is_hindi:
            hindi_queries.append(query['query_score']['query_weighted_total'])
        else:
            english_queries.append(query['query_score']['query_weighted_total'])
        
        # Process device components
        for device in query['devices']:
            if is_hindi:
                hindi_components['device_score'].append(device['score']['device_score'])
                hindi_components['task_type_score'].append(device['score']['task_type_score'])
                hindi_components['mode_score'].append(device['score']['mode_score'])
                hindi_components['args_score'].append(device['score']['args_score'])
            else:
                english_components['device_score'].append(device['score']['device_score'])
                english_components['task_type_score'].append(device['score']['task_type_score'])
                english_components['mode_score'].append(device['score']['mode_score'])
                english_components['args_score'].append(device['score']['args_score'])
                
    return {
        'hindi_avg': sum(hindi_queries)/len(hindi_queries) if hindi_queries else 0,
        'english_avg': sum(english_queries)/len(english_queries) if english_queries else 0,
        'hindi_count': len(hindi_queries),
        'english_count': len(english_queries),
        'hindi_components': {k: sum(v)/len(v) if v else 0 for k, v in hindi_components.items()},
        'english_components': {k: sum(v)/len(v) if v else 0 for k, v in english_components.items()}
    }

def analyze_complexity(data):
    """Analyze performance based on query complexity"""
    simple_queries = []  # Queries with 1 device
    complex_queries = []  # Queries with multiple devices
    
    simple_components = {
        'device_score': [],
        'task_type_score': [],
        'mode_score': [],
        'args_score': []
    }
    
    complex_components = {
        'device_score': [],
        'task_type_score': [],
        'mode_score': [],
        'args_score': []
    }
    
    for query in data['query_scores']:
        complexity = 'simple' if len(query['devices']) == 1 else 'complex'
        
        # Add the query's weighted score to the appropriate list
        if complexity == 'simple':
            simple_queries.append(query['query_score']['query_weighted_total'])
        else:
            complex_queries.append(query['query_score']['query_weighted_total'])
        
        # Process device components
        for device in query['devices']:
            if complexity == 'simple':
                simple_components['device_score'].append(device['score']['device_score'])
                simple_components['task_type_score'].append(device['score']['task_type_score'])
                simple_components['mode_score'].append(device['score']['mode_score'])
                simple_components['args_score'].append(device['score']['args_score'])
            else:
                complex_components['device_score'].append(device['score']['device_score'])
                complex_components['task_type_score'].append(device['score']['task_type_score'])
                complex_components['mode_score'].append(device['score']['mode_score'])
                complex_components['args_score'].append(device['score']['args_score'])
                
    return {
        'simple_avg': sum(simple_queries)/len(simple_queries) if simple_queries else 0,
        'complex_avg': sum(complex_queries)/len(complex_queries) if complex_queries else 0,
        'simple_count': len(simple_queries),
        'complex_count': len(complex_queries),
        'simple_components': {k: sum(v)/len(v) if v else 0 for k, v in simple_components.items()},
        'complex_components': {k: sum(v)/len(v) if v else 0 for k, v in complex_components.items()}
    }

def analyze_task_types(data):
    """Analyze performance based on task types (concurrent vs sequential)"""
    concurrent_tasks = []
    sequential_tasks = []
    
    for query in data['query_scores']:
        for device in query['devices']:
            task_type = device['actual']['task_type']
            if task_type == 'concurrent':
                concurrent_tasks.append(device['score']['weighted_total'])
            elif task_type == 'sequential':
                sequential_tasks.append(device['score']['weighted_total'])
    
    return {
        'concurrent_avg': sum(concurrent_tasks)/len(concurrent_tasks) if concurrent_tasks else 0,
        'sequential_avg': sum(sequential_tasks)/len(sequential_tasks) if sequential_tasks else 0,
        'concurrent_count': len(concurrent_tasks),
        'sequential_count': len(sequential_tasks)
    }

def analyze_mode_performance(data):
    """Analyze performance based on device modes"""
    mode_metrics = defaultdict(lambda: {
        'total': 0, 
        'score': 0,
        'device': None
    })
    
    for query in data['query_scores']:
        for device in query['devices']:
            if device['actual']['mode']:
                mode = device['actual']['mode']
                mode_metrics[mode]['total'] += 1
                mode_metrics[mode]['score'] += device['score']['mode_score']
                mode_metrics[mode]['device'] = device['actual']['device']
    
    # Convert to averages
    for mode in mode_metrics:
        total = mode_metrics[mode]['total']
        mode_metrics[mode]['score'] /= total
            
    return dict(mode_metrics)

def analyze_args_performance(data):
    """Analyze performance based on argument types"""
    args_metrics = defaultdict(lambda: {
        'total': 0,
        'score': 0
    })
    
    for query in data['query_scores']:
        for device in query['devices']:
            if device['actual']['args']:
                for arg_key in device['actual']['args']:
                    args_metrics[arg_key]['total'] += 1
                    
                    # Check if this arg was correctly predicted
                    predicted_args = device['predicted'].get('args', {})
                    if arg_key in predicted_args and predicted_args[arg_key] == device['actual']['args'][arg_key]:
                        args_metrics[arg_key]['score'] += 1
    
    # Convert to percentages
    for arg in args_metrics:
        total = args_metrics[arg]['total']
        args_metrics[arg]['score'] = (args_metrics[arg]['score'] / total) * 100 if total > 0 else 0
            
    return dict(args_metrics)

def extract_query_data(data):
    """Extract query-level data for individual analysis"""
    query_data = []
    
    for query in data['query_scores']:
        is_hindi = any(ord('\u0900') <= ord(c) <= ord('\u097F') for c in query['query'])
        
        query_data.append({
            'query': query['query'],
            'language': 'Hindi' if is_hindi else 'English',
            'complexity': 'Complex' if len(query['devices']) > 1 else 'Simple',
            'device_count': len(query['devices']),
            'weighted_total': query['query_score']['query_weighted_total'],
            'device_score': query['query_score']['query_device_score'],
            'task_type_score': query['query_score']['query_task_type_score'],
            'mode_score': query['query_score']['query_mode_score'],
            'args_score': query['query_score']['query_args_score']
        })
    
    return query_data

def create_dashboard():
    st.set_page_config(layout="wide", page_title="IoT Agent Evaluation Dashboard")
    
    st.title("IoT Agent Evaluation Analysis Dashboard")
    st.markdown("""
    This comprehensive dashboard provides detailed analysis of your IoT agent's performance in understanding and executing user commands.
    Upload your evaluation JSON file to begin analysis.
    """)
    
    # File uploader
    uploaded_file = st.file_uploader("Upload JSON evaluation file", type=['json'])
    
    if uploaded_file is not None:
        # Load the data
        global data
        data = json.load(uploaded_file)
        
        # Dashboard tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "Overall Performance", 
            "Device Analysis", 
            "Language Analysis", 
            "Complexity Analysis",
            "Component Analysis",
            "Individual Queries",
            "Custom Insights",
            "Export"
        ])
        
        # Overall metrics
        with tab1:
            st.header("Overall Performance Metrics")
            
            # Calculate metrics
            total_queries = len(data['query_scores'])
            total_devices = sum(len(query['devices']) for query in data['query_scores'])
            
            # Create metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Overall Average Score", f"{data['overall_average']:.3f}")
            with col2:
                st.metric("Total Queries", total_queries)
            with col3:
                st.metric("Total Devices", total_devices)
            with col4:
                avg_devices = total_devices / total_queries if total_queries > 0 else 0
                st.metric("Avg Devices per Query", f"{avg_devices:.2f}")
            
            component_scores = {
                'Device Recognition': 0,
                'Task Type Recognition': 0,
                'Mode Recognition': 0,
                'Args Parsing': 0
            }
            total_devices = sum(len(query['devices']) for query in data['query_scores'])

            for query in data['query_scores']:
                for device in query['devices']:
                    component_scores['Device Recognition'] += device['score']['device_score']
                    component_scores['Task Type Recognition'] += device['score']['task_type_score']
                    component_scores['Mode Recognition'] += device['score']['mode_score']
                    component_scores['Args Parsing'] += device['score']['args_score']

            # Convert to averages
            for component in component_scores:
                component_scores[component] /= total_devices
            # Plot component scores
            fig = px.bar(
                x=list(component_scores.keys()),
                y=list(component_scores.values()),
                title="Overall Component Performance",
                labels={'x': 'Component', 'y': 'Average Score'},
                color=list(component_scores.keys()),
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(xaxis_title="Component", yaxis_title="Average Score")
            st.plotly_chart(fig, use_container_width=True)
            
            # Success rate by threshold (device-level)
            st.subheader("Success Rate by Threshold")

            thresholds = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            success_rates = []
            total_devices = sum(len(query['devices']) for query in data['query_scores'])

            for threshold in thresholds:
                success_count = 0
                for query in data['query_scores']:
                    for device in query['devices']:
                        if device['score']['weighted_total'] >= threshold:
                            success_count += 1
                success_rates.append((success_count / total_devices) * 100)
            
            # Plot success rates
            fig = px.line(
                x=thresholds,
                y=success_rates,
                title="Success Rate by Score Threshold",
                labels={'x': 'Threshold', 'y': 'Success Rate (%)'},
                markers=True
            )
            fig.update_layout(xaxis_title="Score Threshold", yaxis_title="Success Rate (%)")
            st.plotly_chart(fig, use_container_width=True)
        
        # Device-specific analysis
        with tab2:
            st.header("Device-wise Performance Analysis")
            
            device_metrics = extract_device_metrics(data)
            
            # Convert to DataFrame for easier plotting
            df_devices = pd.DataFrame.from_dict(device_metrics, orient='index')
            
            # Bar chart of device success rates
            fig = px.bar(
                df_devices,
                y=df_devices.index,
                x='success_rate',
                title="Device Success Rates",
                labels={'index': 'Device', 'success_rate': 'Success Rate (%)'},
                orientation='h',
                color='success_rate',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            fig.update_layout(yaxis_title="Device", xaxis_title="Success Rate (%)")
            st.plotly_chart(fig, use_container_width=True)
            
            # Component performance heatmap
            component_cols = ['device_score', 'task_type_score', 'mode_score', 'args_score']
            fig = px.imshow(
                df_devices[component_cols],
                labels=dict(x="Component", y="Device", color="Score"),
                x=['Device Recognition', 'Task Type', 'Mode', 'Arguments'],
                y=df_devices.index,
                title="Device Performance by Component",
                color_continuous_scale="Viridis"
            )
            fig.update_layout(
                xaxis_title="Component", 
                yaxis_title="Device",
                height=400 + (len(device_metrics) * 30)  # Adjust height based on number of devices
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Device frequency
            st.subheader("Device Frequency Distribution")
            device_counts = {device: metrics['total'] for device, metrics in device_metrics.items()}
            fig = px.pie(
                names=list(device_counts.keys()),
                values=list(device_counts.values()),
                title="Device Distribution in Queries",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Device performance table
            st.subheader("Device Performance Details")
            
            formatted_df = df_devices.copy()
            for col in component_cols + ['weighted_total', 'success_rate']:
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2f}" if col != 'success_rate' else f"{x:.2f}%")
            
            formatted_df = formatted_df.rename(columns={
                'total': 'Occurrences',
                'device_score': 'Device Recognition',
                'task_type_score': 'Task Type',
                'mode_score': 'Mode',
                'args_score': 'Arguments',
                'weighted_total': 'Average Score',
                'success_rate': 'Success Rate',
                'failure_count': 'Failures'
            })
            
            st.dataframe(formatted_df[['Occurrences', 'Device Recognition', 'Task Type', 'Mode', 
                                      'Arguments', 'Average Score', 'Success Rate', 'Failures']], 
                        use_container_width=True)
        
        # Language analysis
        with tab3:
            st.header("Language Performance Analysis")
            lang_metrics = analyze_language_performance(data)
            
            col1, col2 = st.columns(2)
            with col1:
                # Average scores by language
                fig = px.bar(
                    x=['Hindi', 'English'],
                    y=[lang_metrics['hindi_avg'], lang_metrics['english_avg']],
                    title="Performance by Language",
                    labels={'x': 'Language', 'y': 'Average Score'},
                    color=['Hindi', 'English'],
                    color_discrete_sequence=['#FF9933', '#138808']  # India flag colors
                )
                fig.update_layout(xaxis_title="Language", yaxis_title="Average Score")
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                # Query distribution by language
                fig = px.pie(
                    names=['Hindi', 'English'],
                    values=[lang_metrics['hindi_count'], lang_metrics['english_count']],
                    title="Query Distribution by Language",
                    hole=0.4,
                    color=['Hindi', 'English'],
                    color_discrete_sequence=['#FF9933', '#138808']
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Component performance by language
            st.subheader("Component Performance by Language")
            
            component_names = ['Device Recognition', 'Task Type Recognition', 'Mode Recognition', 'Args Parsing']
            hindi_scores = [lang_metrics['hindi_components'][comp] for comp in ['device_score', 'task_type_score', 'mode_score', 'args_score']]
            english_scores = [lang_metrics['english_components'][comp] for comp in ['device_score', 'task_type_score', 'mode_score', 'args_score']]
            
            fig = go.Figure(data=[
                go.Bar(name='Hindi', x=component_names, y=hindi_scores, marker_color='#FF9933'),
                go.Bar(name='English', x=component_names, y=english_scores, marker_color='#138808')
            ])
            fig.update_layout(
                barmode='group',
                title="Component Performance by Language",
                xaxis_title="Component",
                yaxis_title="Average Score"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Example queries by language
            st.subheader("Sample Queries by Language")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Hindi Queries**")
                hindi_queries = [q['query'] for q in data['query_scores'] 
                               if any(ord('\u0900') <= ord(c) <= ord('\u097F') for c in q['query'])]
                for query in hindi_queries[:5]:  # Show top 5 Hindi queries
                    st.info(query)
            
            with col2:
                st.markdown("**English Queries**")
                english_queries = [q['query'] for q in data['query_scores'] 
                                 if not any(ord('\u0900') <= ord(c) <= ord('\u097F') for c in q['query'])]
                for query in english_queries[:5]:  # Show top 5 English queries
                    st.info(query)
        
        # Complexity analysis
        with tab4:
            st.header("Query Complexity Analysis")
            complexity_metrics = analyze_complexity(data)
            
            col1, col2 = st.columns(2)
            with col1:
                # Average scores by complexity
                fig = px.bar(
                    x=['Simple Queries', 'Complex Queries'],
                    y=[complexity_metrics['simple_avg'], complexity_metrics['complex_avg']],
                    title="Performance by Query Complexity",
                    labels={'x': 'Query Type', 'y': 'Average Score'},
                    color=['Simple Queries', 'Complex Queries'],
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_layout(xaxis_title="Query Type", yaxis_title="Average Score")
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                # Query distribution by complexity
                fig = px.pie(
                    names=['Simple Queries', 'Complex Queries'],
                    values=[complexity_metrics['simple_count'], complexity_metrics['complex_count']],
                    title="Query Distribution by Complexity",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Component performance by complexity
            st.subheader("Component Performance by Complexity")
            
            component_names = ['Device Recognition', 'Task Type Recognition', 'Mode Recognition', 'Args Parsing']
            simple_scores = [complexity_metrics['simple_components'][comp] for comp in ['device_score', 'task_type_score', 'mode_score', 'args_score']]
            complex_scores = [complexity_metrics['complex_components'][comp] for comp in ['device_score', 'task_type_score', 'mode_score', 'args_score']]
            
            fig = go.Figure(data=[
                go.Bar(name='Simple Queries', x=component_names, y=simple_scores),
                go.Bar(name='Complex Queries', x=component_names, y=complex_scores)
            ])
            fig.update_layout(
                barmode='group',
                title="Component Performance by Query Complexity",
                xaxis_title="Component",
                yaxis_title="Average Score"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Task type analysis
            st.subheader("Task Type Analysis")
            task_metrics = analyze_task_types(data)
            
            col1, col2 = st.columns(2)
            with col1:
                # Average scores by task type
                fig = px.bar(
                    x=['Concurrent', 'Sequential'],
                    y=[task_metrics['concurrent_avg'], task_metrics['sequential_avg']],
                    title="Performance by Task Type",
                    labels={'x': 'Task Type', 'y': 'Average Score'},
                    color=['Concurrent', 'Sequential'],
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_layout(xaxis_title="Task Type", yaxis_title="Average Score")
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                # Task distribution by type
                fig = px.pie(
                    names=['Concurrent', 'Sequential'],
                    values=[task_metrics['concurrent_count'], task_metrics['sequential_count']],
                    title="Task Distribution by Type",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Component analysis
        with tab5:
            st.header("Component-level Analysis")
            
            # Mode performance analysis
            st.subheader("Mode Recognition Performance")
            mode_metrics = analyze_mode_performance(data)
            
            # Convert to DataFrame for easier plotting
            mode_df = pd.DataFrame.from_dict(mode_metrics, orient='index')
            
            # Sort by score
            mode_df = mode_df.sort_values('score', ascending=False)
            
            # Plot mode scores
            fig = px.bar(
                mode_df,
                y=mode_df.index,
                x='score',
                title="Mode Recognition Performance",
                labels={'index': 'Mode', 'score': 'Recognition Score'},
                orientation='h',
                color='device',
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig.update_layout(
                yaxis_title="Mode", 
                xaxis_title="Recognition Score",
                height=400 + (len(mode_metrics) * 20)  # Adjust height based on number of modes
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Args performance analysis
            st.subheader("Arguments Parsing Performance")
            args_metrics = analyze_args_performance(data)
            
            if args_metrics:
                # Convert to DataFrame for easier plotting
                args_df = pd.DataFrame.from_dict(args_metrics, orient='index')
                
                # Sort by score
                args_df = args_df.sort_values('score', ascending=False)
                
                # Plot args scores
                fig = px.bar(
                    args_df,
                    y=args_df.index,
                    x='score',
                    title="Arguments Parsing Performance",
                    labels={'index': 'Argument Type', 'score': 'Recognition Score (%)'},
                    orientation='h',
                    color=args_df.index,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_layout(
                    yaxis_title="Argument Type", 
                    xaxis_title="Recognition Score (%)",
                    height=400 + (len(args_metrics) * 30)  # Adjust height based on number of arg types
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No argument data available for analysis.")
            
            # Failure analysis
            st.subheader("Failure Analysis")
            
            # Calculate failure rates for each component
            failure_metrics = {
                'Device Recognition': 0,
                'Task Type Recognition': 0,
                'Mode Recognition': 0,
                'Args Parsing': 0
            }
            
            total_interactions = 0
            for query in data['query_scores']:
                for device in query['devices']:
                    total_interactions += 1
                    if device['score']['device_score'] == 0:
                        failure_metrics['Device Recognition'] += 1
                    if device['score']['task_type_score'] == 0:
                        failure_metrics['Task Type Recognition'] += 1
                    if device['score']['mode_score'] == 0:
                        failure_metrics['Mode Recognition'] += 1
                    if device['score']['args_score'] == 0:
                        failure_metrics['Args Parsing'] += 1
            
            # Convert to percentages
            for metric in failure_metrics:
                failure_metrics[metric] = (failure_metrics[metric] / total_interactions) * 100 if total_interactions > 0 else 0
                
            # Plot failure rates
            fig = px.bar(
                x=list(failure_metrics.keys()),
                y=list(failure_metrics.values()),
                title="Failure Rates by Component",
                labels={'x': 'Component', 'y': 'Failure Rate (%)'},
                color=list(failure_metrics.keys()),
                color_discrete_sequence=px.colors.sequential.Reds_r
            )
            fig.update_layout(xaxis_title="Component", yaxis_title="Failure Rate (%)")
            st.plotly_chart(fig, use_container_width=True)
        
        # Individual query analysis
        with tab6:
            st.header("Individual Query Analysis")
            
            query_data = extract_query_data(data)
            query_df = pd.DataFrame(query_data)
            
            # Add success/failure classification
            threshold = st.slider("Success Threshold", 0.0, 1.0, 0.7, 0.1)
            query_df['status'] = query_df['weighted_total'].apply(lambda x: 'Success' if x >= threshold else 'Failure')
            
            # Filter options
            st.subheader("Filter Queries")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                language_filter = st.multiselect("Language", ['Hindi', 'English'], default=['Hindi', 'English'])
            with col2:
                complexity_filter = st.multiselect("Complexity", ['Simple', 'Complex'], default=['Simple', 'Complex'])
            with col3:
                status_filter = st.multiselect("Status", ['Success', 'Failure'], default=['Success', 'Failure'])
            
            # Apply filters
            filtered_df = query_df[
                (query_df['language'].isin(language_filter)) & 
                (query_df['complexity'].isin(complexity_filter)) &
                (query_df['status'].isin(status_filter))
            ]
            
            # Show filtered queries
            st.subheader(f"Queries ({len(filtered_df)} results)")
            
            if not filtered_df.empty:
                # Sort options
                sort_by = st.selectbox("Sort by", ['weighted_total', 'device_count', 'language', 'complexity'])
                filtered_df = filtered_df.sort_values(by=sort_by, ascending=False)
                
                # Display queries
                for i, row in filtered_df.iterrows():
                    with st.expander(f"{row['query'][:100]}{'...' if len(row['query']) > 100 else ''}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"**Query:** {row['query']}")
                            st.markdown(f"**Language:** {row['language']}")
                            st.markdown(f"**Complexity:** {row['complexity']} ({row['device_count']} devices)")
                            st.markdown(f"**Status:** {row['status']}")
                        
                        with col2:
                            st.markdown("**Scores:**")
                            st.markdown(f"- Overall: {row['weighted_total']:.2f}")
                            st.markdown(f"- Device Recognition: {row['device_score']:.2f}")
                            st.markdown(f"- Task Type: {row['task_type_score']:.2f}")
                            st.markdown(f"- Mode: {row['mode_score']:.2f}")
                            st.markdown(f"- Arguments: {row['args_score']:.2f}")
                            
                            # Calculate component that caused failure
                            if row['status'] == 'Failure':
                                components = {
                                    'Device Recognition': row['device_score'],
                                    'Task Type': row['task_type_score'],
                                    'Mode': row['mode_score'],
                                    'Arguments': row['args_score']
                                }
                                
                                failed_components = [comp for comp, score in components.items() if score < threshold]
                                if failed_components:
                                    st.markdown("**Failed Components:**")
                                    for comp in failed_components:
                                        st.markdown(f"- {comp}")
            else:
                st.info("No queries match the selected filters.")
            
            # Export functionality
            st.download_button(
                "Export Filtered Data",
                filtered_df.to_csv(index=False).encode('utf-8'),
                "filtered_queries.csv",
                "text/csv",
                key='download-csv'
            )
            
            # Query pattern analysis
            st.subheader("Query Pattern Insights")
            
            if not filtered_df.empty:
                # Score distribution histogram
                fig = px.histogram(
                    filtered_df, 
                    x="weighted_total",
                    color="language",
                    title="Query Score Distribution",
                    nbins=20,
                    opacity=0.7
                )
                fig.update_layout(xaxis_title="Overall Score", yaxis_title="Number of Queries")
                st.plotly_chart(fig, use_container_width=True)
                
                # Success rate by query characteristics
                st.markdown("### Success Rate Analysis")
                
                # By language
                lang_success = filtered_df.groupby('language')['status'].apply(
                    lambda x: (x == 'Success').mean() * 100
                ).reset_index()
                lang_success.columns = ['Language', 'Success Rate (%)']
                
                # By complexity
                complexity_success = filtered_df.groupby('complexity')['status'].apply(
                    lambda x: (x == 'Success').mean() * 100
                ).reset_index()
                complexity_success.columns = ['Complexity', 'Success Rate (%)']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.bar(
                        lang_success,
                        x='Language',
                        y='Success Rate (%)',
                        title="Success Rate by Language",
                        color='Language'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.bar(
                        complexity_success,
                        x='Complexity',
                        y='Success Rate (%)',
                        title="Success Rate by Complexity",
                        color='Complexity'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        # New custom insights tab (tab7)
        with tab7:
            custom_viz_tab()
        
        # New export tab (tab8)
        with tab8:
            export_tab()
        
        # Advanced filters in sidebar
        advanced_filters_tab()

def analyze_error_patterns(data):
    """Identify common error patterns in the data"""
    error_patterns = defaultdict(int)
    device_errors = defaultdict(lambda: defaultdict(int))
    
    # Track which components fail together
    component_cooccurrence = {
        'device_task': 0,
        'device_mode': 0,
        'device_args': 0,
        'task_mode': 0,
        'task_args': 0,
        'mode_args': 0,
        'all_components': 0
    }
    
    total_devices = 0
    
    for query in data['query_scores']:
        for device in query['devices']:
            total_devices += 1
            device_name = device['actual']['device']
            
            # Track individual component errors
            components_failed = []
            
            if device['score']['device_score'] == 0:
                error_patterns['device_recognition'] += 1
                device_errors[device_name]['device'] += 1
                components_failed.append('device')
                
            if device['score']['task_type_score'] == 0:
                error_patterns['task_type_recognition'] += 1
                device_errors[device_name]['task'] += 1
                components_failed.append('task')
                
            if device['score']['mode_score'] == 0:
                error_patterns['mode_recognition'] += 1
                device_errors[device_name]['mode'] += 1
                components_failed.append('mode')
                
            if device['score']['args_score'] == 0:
                error_patterns['args_parsing'] += 1
                device_errors[device_name]['args'] += 1
                components_failed.append('args')
            
            # Track co-occurrence of failures
            if 'device' in components_failed and 'task' in components_failed:
                component_cooccurrence['device_task'] += 1
            if 'device' in components_failed and 'mode' in components_failed:
                component_cooccurrence['device_mode'] += 1
            if 'device' in components_failed and 'args' in components_failed:
                component_cooccurrence['device_args'] += 1
            if 'task' in components_failed and 'mode' in components_failed:
                component_cooccurrence['task_mode'] += 1
            if 'task' in components_failed and 'args' in components_failed:
                component_cooccurrence['task_args'] += 1
            if 'mode' in components_failed and 'args' in components_failed:
                component_cooccurrence['mode_args'] += 1
            if len(components_failed) == 4:
                component_cooccurrence['all_components'] += 1
    
    # Convert to percentages
    for pattern in error_patterns:
        error_patterns[pattern] = (error_patterns[pattern] / total_devices) * 100
        
    for device in device_errors:
        for component in device_errors[device]:
            device_errors[device][component] = (device_errors[device][component] / total_devices) * 100
            
    for pattern in component_cooccurrence:
        component_cooccurrence[pattern] = (component_cooccurrence[pattern] / total_devices) * 100
    
    return {
        'error_patterns': error_patterns,
        'device_errors': device_errors,
        'component_cooccurrence': component_cooccurrence
    }

def custom_viz_tab():
    """Create custom visualizations tab"""
    st.header("Custom Visualizations")
    
    st.subheader("Error Pattern Analysis")
    
    error_data = analyze_error_patterns(data)
    
    # Error pattern heatmap
    device_error_data = []
    for device, errors in error_data['device_errors'].items():
        for component, rate in errors.items():
            device_error_data.append({
                'Device': device,
                'Component': component.capitalize(),
                'Error Rate (%)': rate
            })
    
    if device_error_data:
        df_errors = pd.DataFrame(device_error_data)
        pivot_df = df_errors.pivot(index='Device', columns='Component', values='Error Rate (%)')
        
        fig = px.imshow(
            pivot_df,
            labels=dict(x="Component", y="Device", color="Error Rate (%)"),
            title="Error Patterns by Device and Component",
            color_continuous_scale="Reds"
        )
        fig.update_layout(
            xaxis_title="Component", 
            yaxis_title="Device",
            height=400 + (len(error_data['device_errors']) * 30)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Component hierarchical analysis
    st.subheader("Recognition Flow Analysis")
    
    # Get component error rates
    device_error = error_data['error_patterns'].get('device_recognition', 0)
    mode_error = error_data['error_patterns'].get('mode_recognition', 0) 
    args_error = error_data['error_patterns'].get('args_parsing', 0)
    
    # Get language metrics for correlation insights
    lang_metrics = analyze_language_performance(data)
    
    # Get complexity metrics
    complexity_metrics = analyze_complexity(data)
    
    # Calculate base flows
    total_flow = 100  # Start with 100% of queries
    
    # Calculate language-specific contributions
    hindi_ratio = lang_metrics['hindi_count'] / (lang_metrics['hindi_count'] + lang_metrics['english_count']) * 100
    english_ratio = 100 - hindi_ratio
    
    # Calculate complexity-specific contributions
    simple_ratio = complexity_metrics['simple_count'] / (complexity_metrics['simple_count'] + complexity_metrics['complex_count']) * 100
    complex_ratio = 100 - simple_ratio
    
    # Define success rates by language and complexity
    hindi_success_rate = lang_metrics['hindi_avg'] * 100
    english_success_rate = lang_metrics['english_avg'] * 100
    simple_success_rate = complexity_metrics['simple_avg'] * 100
    complex_success_rate = complexity_metrics['complex_avg'] * 100
    
    # Calculate flows
    hindi_flow = total_flow * hindi_ratio / 100
    english_flow = total_flow * english_ratio / 100
    
    # Success rates for different pathways
    device_success_rate = 100 - device_error
    mode_success_rate = 100 - mode_error
    args_success_rate = 100 - args_error
    
    # Calculate language-specific success flows
    hindi_success_flow = hindi_flow * hindi_success_rate / 100
    english_success_flow = english_flow * english_success_rate / 100
    
    # Calculate complexity-specific flows
    # We'll split the Hindi and English flows into simple and complex
    hindi_simple_flow = hindi_flow * simple_ratio / 100
    hindi_complex_flow = hindi_flow * complex_ratio / 100
    english_simple_flow = english_flow * simple_ratio / 100
    english_complex_flow = english_flow * complex_ratio / 100
    
    # Calculate success flow for each complexity category
    hindi_simple_success = hindi_simple_flow * simple_success_rate / 100
    hindi_complex_success = hindi_complex_flow * complex_success_rate / 100
    english_simple_success = english_simple_flow * simple_success_rate / 100
    english_complex_success = english_complex_flow * complex_success_rate / 100
    
    # Calculate failure flows
    hindi_simple_failure = hindi_simple_flow - hindi_simple_success
    hindi_complex_failure = hindi_complex_flow - hindi_complex_success
    english_simple_failure = english_simple_flow - english_simple_success
    english_complex_failure = english_complex_flow - english_complex_success
    
    # Colors for visualization - use a cohesive color scheme
    language_colors = {
        'hindi': "rgba(255, 153, 51, 0.7)",     # Orange from Indian flag
        'english': "rgba(19, 136, 8, 0.7)"      # Green from Indian flag
    }
    complexity_colors = {
        'simple': "rgba(54, 162, 235, 0.7)",    # Blue
        'complex': "rgba(153, 102, 255, 0.7)"   # Purple
    }
    outcome_colors = {
        'success': "rgba(75, 192, 192, 0.7)",   # Teal
        'failure': "rgba(255, 99, 132, 0.7)"    # Pink/Red
    }
    
    # Create nodes for the Sankey diagram
    nodes = [
        # Input nodes - Languages
        {'id': 'hindi', 'name': 'Hindi Queries', 'color': language_colors['hindi']},
        {'id': 'english', 'name': 'English Queries', 'color': language_colors['english']},
        
        # Middle nodes - Complexity
        {'id': 'hindi_simple', 'name': 'Hindi Simple', 'color': complexity_colors['simple']},
        {'id': 'hindi_complex', 'name': 'Hindi Complex', 'color': complexity_colors['complex']},
        {'id': 'english_simple', 'name': 'English Simple', 'color': complexity_colors['simple']},
        {'id': 'english_complex', 'name': 'English Complex', 'color': complexity_colors['complex']},
        
        # Recognition pathways
        {'id': 'recognition', 'name': 'Recognition Pipeline', 'color': "rgba(128, 128, 128, 0.7)"},
        
        # Component-level nodes
        {'id': 'device', 'name': 'Device Recognition', 'color': "rgba(128, 128, 128, 0.7)"},
        {'id': 'mode', 'name': 'Mode Recognition', 'color': "rgba(128, 128, 128, 0.7)"},
        {'id': 'args', 'name': 'Args Recognition', 'color': "rgba(128, 128, 128, 0.7)"},
        
        # Outcome nodes
        {'id': 'success', 'name': 'Successful Recognition', 'color': outcome_colors['success']},
        {'id': 'failure', 'name': 'Failed Recognition', 'color': outcome_colors['failure']}
    ]
    
    # Create links data showing correlations
    links = [
        # Language to complexity type
        {'source': 'hindi', 'target': 'hindi_simple', 'value': hindi_simple_flow, 'color': language_colors['hindi']},
        {'source': 'hindi', 'target': 'hindi_complex', 'value': hindi_complex_flow, 'color': language_colors['hindi']},
        {'source': 'english', 'target': 'english_simple', 'value': english_simple_flow, 'color': language_colors['english']},
        {'source': 'english', 'target': 'english_complex', 'value': english_complex_flow, 'color': language_colors['english']},
        
        # Complexity to outcome
        {'source': 'hindi_simple', 'target': 'recognition', 'value': hindi_simple_flow, 'color': complexity_colors['simple']},
        {'source': 'hindi_complex', 'target': 'recognition', 'value': hindi_complex_flow, 'color': complexity_colors['complex']},
        {'source': 'english_simple', 'target': 'recognition', 'value': english_simple_flow, 'color': complexity_colors['simple']},
        {'source': 'english_complex', 'target': 'recognition', 'value': english_complex_flow, 'color': complexity_colors['complex']},
        
        # Recognition pipeline
        {'source': 'recognition', 'target': 'device', 'value': total_flow, 'color': "rgba(128, 128, 128, 0.7)"},
        {'source': 'device', 'target': 'mode', 'value': total_flow * device_success_rate / 100, 'color': "rgba(128, 128, 128, 0.7)"},
        {'source': 'mode', 'target': 'args', 'value': total_flow * device_success_rate / 100 * mode_success_rate / 100, 'color': "rgba(128, 128, 128, 0.7)"},
        
        # Failed at each step
        {'source': 'device', 'target': 'failure', 'value': total_flow * device_error / 100, 'color': outcome_colors['failure']},
        {'source': 'mode', 'target': 'failure', 'value': total_flow * device_success_rate / 100 * mode_error / 100, 'color': outcome_colors['failure']},
        {'source': 'args', 'target': 'failure', 'value': total_flow * device_success_rate / 100 * mode_success_rate / 100 * args_error / 100, 'color': outcome_colors['failure']},
        
        # Success at the end
        {'source': 'args', 'target': 'success', 'value': total_flow * device_success_rate / 100 * mode_success_rate / 100 * args_success_rate / 100, 'color': outcome_colors['success']}
    ]
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        arrangement = "freeform",  # Using freeform for better layout
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = [node['name'] for node in nodes],
            color = [node['color'] for node in nodes]
        ),
        link = dict(
            source = [nodes.index(next(node for node in nodes if node['id'] == link['source'])) for link in links],
            target = [nodes.index(next(node for node in nodes if node['id'] == link['target'])) for link in links],
            value = [max(0.5, link['value']) for link in links],  # Ensure minimum visibility for small flows
            color = [link['color'] for link in links]
        )
    )])
    
    fig.update_layout(
        title_text="Query Flow: From Language and Complexity to Recognition Outcome",
        font=dict(size=12),
        height=700
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Show success rates
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Overall Success Rate", f"{args_success_rate:.1f}%")
    
    with col2:
        lang_diff = hindi_success_rate - english_success_rate
        better_lang = "Hindi" if lang_diff > 0 else "English"
        st.metric(f"Better Language", better_lang, f"{abs(lang_diff):.1f}%")
    
    with col3:
        complexity_diff = simple_success_rate - complex_success_rate
        st.metric("Simple vs Complex", f"{complexity_diff:.1f}%", help="Difference in success rates between simple and complex queries")
    
    # Explanation of the threshold graph
    st.subheader("Understanding the Success Rate Threshold Graph")
    st.markdown("""
    The **Success Rate by Threshold** graph (found in the Overall Performance tab) shows how the system's success 
    rate changes as you adjust the score threshold that determines what counts as a "successful" recognition. 
    
    - A threshold of 0.5 means that any recognition with a score ≥ 0.5 is considered successful
    - A threshold of 0.9 is much stricter, requiring near-perfect recognition
    - The graph helps identify the optimal threshold based on your application's requirements
    
    This is useful for understanding how strict or lenient your evaluation criteria should be based on your use case.
    """)
    
    st.subheader("Recommendations")
    
    # Generate recommendations based on analysis
    recommendations = []
    
    # Look at overall component performance
    component_failures = error_data['error_patterns']
    worst_component = max(component_failures.items(), key=lambda x: x[1])
    
    if worst_component[1] > 30:  # If error rate > 30%
        recommendations.append(f"Focus on improving {worst_component[0].replace('_', ' ')} as it has the highest failure rate ({worst_component[1]:.2f}%).")
    
    # Look at device-specific issues
    device_issues = {}
    for device, errors in error_data['device_errors'].items():
        if any(rate > 40 for rate in errors.values()):  # If any component for a device has > 40% error
            worst_comp = max(errors.items(), key=lambda x: x[1])
            device_issues[device] = (worst_comp[0], worst_comp[1])
    
    if device_issues:
        for device, (component, rate) in device_issues.items():
            recommendations.append(f"The '{device}' device has poor {component} recognition ({rate:.2f}% failure rate). Consider retraining with more examples.")
    
    # Look at language performance
    lang_diff = abs(lang_metrics['hindi_avg'] - lang_metrics['english_avg'])
    
    if lang_diff > 0.2:  # If significant difference between languages
        worse_lang = "Hindi" if lang_metrics['hindi_avg'] < lang_metrics['english_avg'] else "English"
        recommendations.append(f"There's a significant performance gap between languages. Focus on improving {worse_lang} query understanding.")
    
    # Display recommendations
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"{i}. {rec}")
    else:
        st.info("No specific recommendations based on current data.")

def advanced_filters_tab():
    """Create advanced filters for deeper analysis"""
    st.header("Advanced Filtering & Analysis")
    
    # Get all unique devices
    all_devices = set()
    for query in data['query_scores']:
        for device in query['devices']:
            all_devices.add(device['actual']['device'])
    
    # Get all unique modes
    all_modes = set()
    for query in data['query_scores']:
        for device in query['devices']:
            if device['actual']['mode']:
                all_modes.add(device['actual']['mode'])
    
    # Sidebar filters
    st.sidebar.header("Advanced Filters")
    
    # Device filter
    selected_devices = st.sidebar.multiselect(
        "Filter by Device",
        list(all_devices),
        default=list(all_devices)
    )
    
    # Mode filter
    selected_modes = st.sidebar.multiselect(
        "Filter by Mode",
        list(all_modes),
        default=list(all_modes)
    )
    
    # Score range filter
    score_range = st.sidebar.slider(
        "Score Range",
        0.0, 1.0, (0.0, 1.0)
    )
    
    # Apply filters to get relevant queries
    filtered_queries = []
    
    for query in data['query_scores']:
        # Check if any device in this query matches our filters
        devices_match = False
        
        for device in query['devices']:
            device_matches = device['actual']['device'] in selected_devices
            mode_matches = True  # Default to True if mode is None
            
            if device['actual']['mode']:
                mode_matches = device['actual']['mode'] in selected_modes
                
            score_matches = score_range[0] <= query['query_score']['query_weighted_total'] <= score_range[1]
            
            if device_matches and mode_matches and score_matches:
                devices_match = True
                break
        
        if devices_match:
            filtered_queries.append(query)
    
    # Display filtered results
    st.subheader(f"Filtered Results ({len(filtered_queries)} queries)")
    
    if filtered_queries:
        # Calculate stats on filtered data
        avg_score = sum(q['query_score']['query_weighted_total'] for q in filtered_queries) / len(filtered_queries)
        
        # Display metrics
        st.metric("Average Score (Filtered)", f"{avg_score:.3f}")
        
        # Detailed analysis on filtered data
        with st.expander("View Filtered Queries"):
            for i, query in enumerate(filtered_queries):
                st.markdown(f"**Query {i+1}:** {query['query']}")
                st.markdown(f"Score: {query['query_score']['query_weighted_total']:.3f}")
                st.markdown("Devices:")
                
                for device in query['devices']:
                    st.markdown(f"- {device['actual']['device']} ({device['score']['weighted_total']:.3f})")
                
                st.markdown("---")
        
        # Compare filtered data with overall
        st.subheader("Comparison with Overall Data")
        
        overall_avg = data['overall_average']
        diff = avg_score - overall_avg
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Filtered Average", f"{avg_score:.3f}")
        with col2:
            st.metric("Overall Average", f"{overall_avg:.3f}")
        with col3:
            st.metric("Difference", f"{diff:.3f}", delta=f"{diff:.3f}")
    else:
        st.info("No queries match the selected filters.")

def export_tab():
    """Create export options for analysis results"""
    st.header("Export Analysis Results")
    
    # Generate summary report
    st.subheader("Summary Report")
    
    report = {}
    
    # Overall metrics
    report['overall'] = {
        'average_score': data['overall_average'],
        'total_queries': len(data['query_scores']),
        'total_devices': sum(len(query['devices']) for query in data['query_scores'])
    }
    
    # Component performance
    component_scores = {
        'device_recognition': 0,
        'task_type_recognition': 0,
        'mode_recognition': 0,
        'args_parsing': 0
    }
    
    for query in data['query_scores']:
        component_scores['device_recognition'] += query['query_score']['query_device_score']
        component_scores['task_type_recognition'] += query['query_score']['query_task_type_score']
        component_scores['mode_recognition'] += query['query_score']['query_mode_score']
        component_scores['args_parsing'] += query['query_score']['query_args_score']
    
    for component in component_scores:
        component_scores[component] /= report['overall']['total_queries']
    
    report['components'] = component_scores
    
    # Language analysis
    lang_metrics = analyze_language_performance(data)
    report['language'] = {
        'hindi_avg': lang_metrics['hindi_avg'],
        'english_avg': lang_metrics['english_avg'],
        'hindi_count': lang_metrics['hindi_count'],
        'english_count': lang_metrics['english_count']
    }
    
    # Complexity analysis
    complexity_metrics = analyze_complexity(data)
    report['complexity'] = {
        'simple_avg': complexity_metrics['simple_avg'],
        'complex_avg': complexity_metrics['complex_avg'],
        'simple_count': complexity_metrics['simple_count'],
        'complex_count': complexity_metrics['complex_count']
    }
    
    # Device performance
    device_metrics = extract_device_metrics(data)
    report['devices'] = device_metrics
    
    # Convert to JSON
    report_json = json.dumps(report, indent=4)
    
    # Display and provide download option
    with st.expander("View Summary Report"):
        st.code(report_json, language="json")
    
    st.download_button(
        "Download Summary Report",
        report_json,
        "iot_agent_analysis_summary.json",
        "application/json",
        key='download-json'
    )
    
    # Export full analysis
    st.subheader("Export Full Analysis")
    
    # Generate CSV of all query scores
    query_data = []
    
    for query in data['query_scores']:
        is_hindi = any(ord('\u0900') <= ord(c) <= ord('\u097F') for c in query['query'])
        
        query_row = {
            'query': query['query'],
            'language': 'Hindi' if is_hindi else 'English',
            'complexity': 'Complex' if len(query['devices']) > 1 else 'Simple',
            'device_count': len(query['devices']),
            'weighted_total': query['query_score']['query_weighted_total'],
            'device_score': query['query_score']['query_device_score'],
            'task_type_score': query['query_score']['query_task_type_score'],
            'mode_score': query['query_score']['query_mode_score'],
            'args_score': query['query_score']['query_args_score']
        }
        
        query_data.append(query_row)
    
    query_df = pd.DataFrame(query_data)
    
    st.download_button(
        "Export All Query Data (CSV)",
        query_df.to_csv(index=False).encode('utf-8'),
        "iot_agent_query_analysis.csv",
        "text/csv",
        key='download-query-csv'
    )
    
    # Export device-level analysis
    device_data = []
    
    for query in data['query_scores']:
        for device in query['devices']:
            is_hindi = any(ord('\u0900') <= ord(c) <= ord('\u097F') for c in query['query'])
            
            device_row = {
                'query': query['query'],
                'language': 'Hindi' if is_hindi else 'English',
                'device': device['actual']['device'],
                'task_type': device['actual']['task_type'],
                'mode': device['actual']['mode'],
                'args': str(device['actual']['args']),
                'weighted_total': device['score']['weighted_total'],
                'device_score': device['score']['device_score'],
                'task_type_score': device['score']['task_type_score'],
                'mode_score': device['score']['mode_score'],
                'args_score': device['score']['args_score']
            }
            
            device_data.append(device_row)
    
    device_df = pd.DataFrame(device_data)
    
    st.download_button(
        "Export Device-Level Data (CSV)",
        device_df.to_csv(index=False).encode('utf-8'),
        "iot_agent_device_analysis.csv",
        "text/csv",
        key='download-device-csv'
    )

if __name__ == "__main__":
    create_dashboard()