import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from database import init_db, add_user, verify_user

# Initialize the database
init_db()

def set_custom_style():
    # Check if dark mode is enabled
    dark_mode = st.session_state.get('dark_mode', False)
    
    # Define colors based on mode
    if dark_mode:
        bg_color = "#0E1117"
        text_color = "#FFFFFF"
        card_bg = "#1F2937"
        input_bg = "#374151"
        button_bg = "#3B82F6"
        button_hover = "#2563EB"
    else:
        bg_color = "#F5F5F5"
        text_color = "#1F2937"
        card_bg = "#FFFFFF"
        input_bg = "#FFFFFF"
        button_bg = "#2196F3"
        button_hover = "#1976D2"

    st.markdown(f"""
        <style>
        /* Main theme */
        .stApp {{
            background-color: {bg_color};
            color: {text_color};
        }}
        
        /* Card-like container */
        .stForm {{
            background-color: {card_bg};
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            margin: 20px 0;
        }}
        
        /* Input fields */
        .stTextInput>div>div>input {{
            background-color: {input_bg};
            color: {text_color};
            border: 2px solid {input_bg};
            border-radius: 5px;
            height: 48px;
            padding: 12px 16px;
            font-size: 16px;
        }}
        
        /* Buttons */
        .stButton>button {{
            background-color: {button_bg};
            color: white;
            border-radius: 5px;
            height: 48px;
            width: 100%;
            font-weight: 600;
            font-size: 16px;
            border: none;
            transition: all 0.3s ease;
        }}
        
        .stButton>button:hover {{
            background-color: {button_hover};
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }}
        
        /* Other styles remain the same */
        </style>
    """, unsafe_allow_html=True)

def login_page():
    set_custom_style()
    
    # Center align the main header
    st.markdown('<h1 class="main-header">Welcome to Data Visualization Dashboard</h1>', unsafe_allow_html=True)
    
    # Create a container for the form
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
            
            with tab1:
                with st.form("login_form"):
                    st.markdown("### Sign In")
                    username = st.text_input("Username", placeholder="Enter your username")
                    password = st.text_input("Password", type="password", placeholder="Enter your password")
                    
                    # Add some spacing
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    submitted = st.form_submit_button("Login")
                    
                    if submitted:
                        if verify_user(username, password):
                            st.markdown('<div class="success-msg">Logged in successfully!</div>', unsafe_allow_html=True)
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = username
                            st.rerun()
                        else:
                            st.markdown('<div class="error-msg">Invalid username or password</div>', unsafe_allow_html=True)
            
            with tab2:
                with st.form("register_form"):
                    st.markdown("### Create Account")
                    new_username = st.text_input("Username", placeholder="Choose a username")
                    new_password = st.text_input("Password", type="password", placeholder="Choose a password")
                    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                    
                    # Add some spacing
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    submitted = st.form_submit_button("Register")
                    
                    if submitted:
                        if new_password != confirm_password:
                            st.markdown('<div class="error-msg">Passwords do not match!</div>', unsafe_allow_html=True)
                        elif len(new_password) < 6:
                            st.markdown('<div class="error-msg">Password must be at least 6 characters long!</div>', unsafe_allow_html=True)
                        else:
                            if add_user(new_username, new_password):
                                st.markdown('<div class="success-msg">Registration successful! Please login.</div>', unsafe_allow_html=True)
                            else:
                                st.markdown('<div class="error-msg">Username already exists!</div>', unsafe_allow_html=True)

def handle_dataframe(df):
    """Pre-process dataframe to handle timestamp and date columns properly"""
    processed_df = df.copy()
    
    for column in processed_df.columns:
        # Skip if column is already numeric
        if pd.api.types.is_numeric_dtype(processed_df[column]):
            continue
            
        # Handle timestamp columns
        if 'month' in column.lower() or 'date' in column.lower() or 'time' in column.lower():
            try:
                # First try parsing as datetime
                processed_df[column] = pd.to_datetime(processed_df[column], errors='coerce')
                
                # If it's a month column, convert to period
                if 'month' in column.lower():
                    processed_df[column] = processed_df[column].dt.to_period('M')
            except Exception as e:
                st.warning(f"Could not convert {column} to datetime: {str(e)}")
                
    return processed_df

def create_visualization(df, column_name, data_type):
    """Create appropriate visualization based on data type"""
    try:
        if data_type == 'numeric':
            # Histogram for numeric data
            fig = px.histogram(df, x=column_name, title=f'Distribution of {column_name}')
            st.plotly_chart(fig, use_container_width=True)
            
            # Box plot
            fig = px.box(df, y=column_name, title=f'Box Plot of {column_name}')
            st.plotly_chart(fig, use_container_width=True)

        elif data_type in ['categorical', 'text']:
            # Bar chart for categorical data
            value_counts = df[column_name].value_counts().head(20)
            fig = px.bar(x=value_counts.index.astype(str), y=value_counts.values, 
                        title=f'Top 20 Categories in {column_name}')
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            if len(value_counts) <= 10:
                fig = px.pie(values=value_counts.values, names=value_counts.index.astype(str), 
                            title=f'Distribution of {column_name}')
                st.plotly_chart(fig, use_container_width=True)

        elif data_type == 'datetime':
            # Create a copy of the datetime column to avoid modifications
            date_col = df[column_name].copy()
            
            # Time series plot
            df_sorted = df.sort_values(column_name)
            fig = px.line(df_sorted, x=column_name, 
                         title=f'Time Series of {column_name}')
            st.plotly_chart(fig, use_container_width=True)
            
            # Monthly distribution
            monthly_data = pd.DataFrame({
                'month': date_col.dt.strftime('%Y-%m'),
                'count': 1
            }).groupby('month').count()
            
            fig = px.bar(x=monthly_data.index, y=monthly_data['count'],
                        title=f'Monthly Distribution of {column_name}')
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"Couldn't create visualization for {column_name}: {str(e)}")

def detect_data_type(column):
    """Detect the data type of a column"""
    # Check for null values
    if column.isnull().all():
        return 'empty'
        
    # Check for datetime
    if pd.api.types.is_datetime64_any_dtype(column):
        return 'datetime'
    
    # Check for numeric
    if pd.api.types.is_numeric_dtype(column):
        # If mostly unique values, treat as numeric
        if column.nunique() / len(column) > 0.5:
            return 'numeric'
        # If few unique values, treat as categorical
        else:
            return 'categorical'
    
    # Check for categorical/text
    if pd.api.types.is_string_dtype(column):
        # If few unique values relative to length, likely categorical
        if column.nunique() / len(column) < 0.5:
            return 'categorical'
        # Otherwise, treat as text
        else:
            return 'text'
    
    # Default to categorical for other types
    return 'categorical'

def main():
    st.set_page_config(page_title="Auto Data Visualizer", layout="wide")
    
    # Initialize dark mode in session state
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    # Add dark mode toggle in sidebar
    with st.sidebar:
        st.session_state.dark_mode = st.toggle("Dark Mode", st.session_state.dark_mode)
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()
    
    # Apply custom styling
    set_custom_style()
    
    # Initialize session state for login
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    # Show login page if not logged in
    if not st.session_state['logged_in']:
        login_page()
        return

    st.title(f"📊 Welcome {st.session_state['username']} to Data Visualization Dashboard")
    st.markdown("Upload your CSV file and get instant visualizations!")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        try:
            # Read the CSV file
            df = pd.read_csv(uploaded_file)
            
            # Pre-process the dataframe
            df = handle_dataframe(df)
            
            # Convert DataFrame to a format streamlit can display
            @st.cache_data
            def convert_df(df):
                return df.to_csv().encode('utf-8')
            
            # Show basic information about the dataset
            st.subheader("📝 Dataset Overview")
            col1, col2, col3 = st.columns(3)
            col1.metric("Rows", df.shape[0])
            col2.metric("Columns", df.shape[1])
            col3.metric("Missing Values", df.isna().sum().sum())
            
            # Display the first few rows
            st.subheader("👀 Data Preview")
            st.dataframe(df.head(), use_container_width=True)
            
            # Create tabs for different types of visualizations
            tabs = st.tabs(["Individual Columns", "Relationships", "Summary Statistics"])
            
            with tabs[0]:
                for column in df.columns:
                    st.markdown(f"### Analysis of {column}")
                    data_type = detect_data_type(df[column])
                    st.write(f"Detected type: {data_type}")
                    create_visualization(df, column, data_type)
                    st.markdown("---")
            
            with tabs[1]:
                # Relationships between columns
                st.subheader("Relationships between Columns")
                numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
                
                if len(numeric_cols) >= 2:
                    col1, col2 = st.columns(2)
                    with col1:
                        x_axis = st.selectbox("Select X axis", numeric_cols)
                    with col2:
                        y_axis = st.selectbox("Select Y axis", numeric_cols)
                    
                    fig = px.scatter(df, x=x_axis, y=y_axis, 
                                   title=f'Scatter Plot: {x_axis} vs {y_axis}')
                    st.plotly_chart(fig, use_container_width=True)
            
            with tabs[2]:
                st.subheader("Summary Statistics")
                st.dataframe(df.describe(), use_container_width=True)
                
        except Exception as e:
            st.error(f"Error occurred: {str(e)}")
            st.error("Please check your CSV file format and try again.")

if __name__ == "__main__":
    main() 
