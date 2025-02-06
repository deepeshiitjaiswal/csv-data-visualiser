import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime
import calendar
import warnings
from database import init_db, add_user, verify_user

# Handle dependencies
try:
    import statsmodels.api as sm
except ImportError:
    st.error("Required package missing. Install with: `pip install statsmodels`")
    st.stop()

# Initialize the database (creates data directory and table if needed)
init_db()

# Suppress datetime warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

def set_custom_style():
    dark_mode = st.session_state.get('dark_mode', False)
    bg_color = "#0E1117" if dark_mode else "#F5F5F5"
    text_color = "#FFFFFF" if dark_mode else "#1F2937"

    st.markdown(f"""
        <style>
        .stApp {{ background-color: {bg_color}; color: {text_color}; }}
        .stDataFrame {{ background-color: {"#1F2937" if dark_mode else "#FFFFFF"} !important; }}
        .stForm {{ background-color: {"#1F2937" if dark_mode else "#FFFFFF"};
                  padding: 30px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }}
        </style>
    """, unsafe_allow_html=True)

def login_page():
    # Allow users to choose dark mode on the login page.
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    st.sidebar.checkbox("Dark Mode", value=st.session_state.dark_mode, key="dark_mode")

    set_custom_style()
    st.markdown('<h1 style="text-align: center;">AI-Powered Data Visualizer</h1>', unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
            with tab1:
                with st.form("login_form"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Login"):
                        if verify_user(username, password):
                            st.session_state.logged_in = True
                            # Attempt to rerun if available; if not, inform the user.
                            if hasattr(st, "experimental_rerun"):
                                st.experimental_rerun()
                            else:
                                st.success("Login successful! (Please refresh your page if necessary.)")
                        else:
                            st.error("Invalid username or password")
            with tab2:
                with st.form("register_form"):
                    new_user = st.text_input("New Username")
                    new_pass = st.text_input("New Password", type="password")
                    if st.form_submit_button("Register"):
                        if add_user(new_user, new_pass):
                            st.success("User registered successfully!")
                        else:
                            st.error("Username already exists. Please choose a different username.")

def smart_datetime_conversion(df):
    """Convert columns to datetime using common format detection."""
    date_formats = [
        '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y',
        '%Y-%m-%d %H:%M:%S', '%d-%b-%y', '%Y%m%d'
    ]

    for col in df.select_dtypes(include='object'):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for fmt in date_formats:
                try:
                    df[col] = pd.to_datetime(df[col], format=fmt, errors='raise')
                    break
                except (ValueError, TypeError):
                    continue
    return df

def generate_ai_narrative(df):
    """
    Generate an AI-powered narrative summary based on the dataset's characteristics.
    """
    narrative = ""
    n_rows, n_cols = df.shape
    narrative += f"**Dataset Overview:**\n- The dataset contains **{n_rows}** rows and **{n_cols}** columns.\n\n"

    # Identify column types.
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = df.select_dtypes(include='object').columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime64[ns]', 'datetimetz']).columns.tolist()

    narrative += f"**Column Types:**\n- **Numeric Columns ({len(numeric_cols)}):** {', '.join(numeric_cols) if numeric_cols else 'None'}\n"
    narrative += f"- **Categorical Columns ({len(categorical_cols)}):** {', '.join(categorical_cols) if categorical_cols else 'None'}\n"
    narrative += f"- **Datetime Columns ({len(datetime_cols)}):** {', '.join(datetime_cols) if datetime_cols else 'None'}\n\n"

    # Basic statistics for numeric columns.
    if numeric_cols:
        stats = df[numeric_cols].describe().T
        top_mean = stats['mean'].idxmax()
        narrative += (f"Among the numeric columns, **{top_mean}** has the highest average value of "
                      f"**{stats.loc[top_mean, 'mean']:.2f}**.\n\n")

    # Correlation analysis for numeric columns.
    if len(numeric_cols) > 1:
        corr = df[numeric_cols].corr().abs()
        corr_stack = corr.stack().reset_index()
        corr_stack = corr_stack[corr_stack['level_0'] != corr_stack['level_1']]
        corr_stack['pairs'] = corr_stack.apply(lambda x: tuple(sorted([x['level_0'], x['level_1']])), axis=1)
        corr_stack = corr_stack.drop_duplicates('pairs')
        if not corr_stack.empty:
            highest_corr = corr_stack.loc[corr_stack[0].idxmax()]
            narrative += (f"The strongest correlation is between **{highest_corr['level_0']}** and **{highest_corr['level_1']}** "
                          f"with a coefficient of **{highest_corr[0]:.2f}**.\n\n")

    # Temporal trend analysis if a datetime and numeric column exist.
    if datetime_cols and numeric_cols:
        date_col = datetime_cols[0]
        numeric_col = numeric_cols[0]
        sorted_df = df.sort_values(by=date_col)
        if not sorted_df.empty:
            start_val = sorted_df[numeric_col].iloc[0]
            end_val = sorted_df[numeric_col].iloc[-1]
            trend = "increased" if end_val > start_val else "decreased"
            narrative += (f"Over time (based on **{date_col}**), **{numeric_col}** appears to have {trend} "
                          f"from **{start_val:.2f}** to **{end_val:.2f}**.\n\n")

    if narrative == "":
        narrative = "Not enough information was detected to generate AI insights."

    return narrative

def generate_insights(df):
    st.header("AI-Generated Insights")

    # Improved datetime handling.
    df = smart_datetime_conversion(df)

    # Univariate Analysis.
    st.subheader("📈 Key Distributions")
    cols = st.columns(3)
    color_palette = px.colors.qualitative.Plotly  # Use a qualitative palette with multiple colors.

    for idx, col in enumerate(df.columns):
        with cols[idx % 3]:
            if pd.api.types.is_numeric_dtype(df[col]):
                # Histogram for numeric columns.
                fig = px.histogram(
                    df, x=col,
                    title=f'{col} Distribution',
                    color_discrete_sequence=[color_palette[idx % len(color_palette)]],
                    template="plotly_white" if not st.session_state.dark_mode else "plotly_dark"
                )
                fig.update_layout(xaxis_title=col, yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                # Timeline for datetime columns.
                df['temp_date'] = df[col].dt.date
                counts = df['temp_date'].value_counts().sort_index()
                fig = px.line(
                    x=counts.index, y=counts.values,
                    title=f'{col} Timeline',
                    markers=True,
                    color_discrete_sequence=px.colors.sequential.Viridis,
                    template="plotly_white" if not st.session_state.dark_mode else "plotly_dark"
                )
                fig.update_layout(xaxis_title="Date", yaxis_title="Frequency")
                st.plotly_chart(fig, use_container_width=True)
            else:
                # Bar chart for categorical columns.
                counts = df[col].value_counts().nlargest(10)
                fig = px.bar(
                    counts,
                    title=f'Top {col} Values',
                    labels={'index': col, 'value': 'Count'},
                    color=counts.index,
                    color_discrete_sequence=px.colors.qualitative.Alphabet,
                    template="plotly_white" if not st.session_state.dark_mode else "plotly_dark"
                )
                st.plotly_chart(fig, use_container_width=True)

    # Correlation Analysis.
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    if len(numeric_cols) > 1:
        st.subheader("🔗 Strongest Correlations")
        try:
            corr_matrix = df[numeric_cols].corr().abs()
            corr_stack = corr_matrix.stack().reset_index()
            # Remove self-correlation entries.
            corr_stack = corr_stack[corr_stack['level_0'] != corr_stack['level_1']]
            # Drop duplicate pairs.
            corr_stack['pairs'] = corr_stack.apply(lambda x: tuple(sorted([x['level_0'], x['level_1']])), axis=1)
            corr_stack = corr_stack.drop_duplicates('pairs')
            top_corr = corr_stack.nlargest(3, 0)

            for _, row in top_corr.iterrows():
                col_x = row['level_0']
                col_y = row['level_1']
                fig = px.scatter(
                    df, x=col_x, y=col_y,
                    trendline='ols',
                    title=f"{col_x} vs {col_y}",
                    color_discrete_sequence=px.colors.qualitative.Set1,
                    template="plotly_white" if not st.session_state.dark_mode else "plotly_dark"
                )
                fig.update_traces(marker=dict(size=8))
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Couldn't calculate correlations: {str(e)}")

    # Temporal Analysis.
    date_cols = df.select_dtypes(include=['datetime', 'datetimetz']).columns.tolist()
    if date_cols:
        st.subheader("⏳ Temporal Trends")
        date_col = date_cols[0]
        # Choose the first available numeric column different from the date column.
        numeric_col = next((col for col in numeric_cols if col != date_col), None)

        if numeric_col:
            try:
                fig = px.line(
                    df, x=date_col, y=numeric_col,
                    title=f'{numeric_col} Over Time',
                    markers=True,
                    color_discrete_sequence=px.colors.sequential.Plasma,
                    template="plotly_white" if not st.session_state.dark_mode else "plotly_dark"
                )
                fig.update_layout(xaxis_title="Date", yaxis_title=numeric_col)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Couldn't plot temporal trend: {str(e)}")

    # AI-Powered Narrative Summary.
    st.subheader("🤖 AI Narrative")
    narrative = generate_ai_narrative(df)
    st.markdown(narrative)

def main():
    st.set_page_config(page_title="AI Data Visualizer", layout="wide")

    # Initialize login status if not present.
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    # If not logged in, show the login page.
    if not st.session_state.logged_in:
        login_page()
        return

    # Sidebar controls for logged-in users.
    set_custom_style()
    st.sidebar.checkbox("Dark Mode", value=st.session_state.dark_mode, key="dark_mode")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        # If st.experimental_rerun exists, call it; otherwise, instruct the user to refresh.
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.info("You have been logged out. Please refresh the page.")
            st.stop()

    st.title("🤖 Smart Data Analysis")
    uploaded_file = st.file_uploader("Upload CSV", type="csv")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            df = smart_datetime_conversion(df)

            st.subheader("Dataset Preview")
            with st.expander("View First 10 Rows"):
                st.dataframe(df.head(10), use_container_width=True)

            generate_insights(df)

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()
