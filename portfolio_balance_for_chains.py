import pandas as pd
import streamlit as st
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from plotly.subplots import make_subplots
import plotly.express as px

pd.options.display.float_format = '{:,.2f}'.format



# Config
st.set_page_config(page_title='Get Etherium Address Balance', page_icon=':bar_chart:', layout='centered',)

# Title
st.title('Portfolio Balance')
st.markdown('This app fetches the balances of given wallets from the Covalent API for multiple chains.')

# Always protect your API keys,
# load api key
load_dotenv()
# To run locally
COVALENT_API_KEY = os.getenv('COVALENT_API_KEY')
# To run in Streamlit Sharing
#COVALENT_API_KEY = st.secrets["COVALENT_API_KEY"]

# Get COVALENT_API_KEY from the user
user_api_key = st.sidebar.text_input("Enter your COVALENT API KEY", "")

api_key_disclaimer = """
Streamlit does not store the data entered into the app between runs, 
so the user's API key won't be stored by Streamlit itself. 
However, it's important to note that this method is not completely secure. 
The input is not masked, meaning that anyone looking at your 
screen could see the API key. Additionally, the API key could 
potentially be stored in browser history or server logs.
"""
st.sidebar.markdown(api_key_disclaimer)

# Check if user API key is provided
if user_api_key:
    COVALENT_API_KEY = user_api_key
elif not st.session_state.get('first_run', True):
    st.sidebar.write("Please enter your COVALENT API KEY to re-run the page.")
    st.stop()

st.session_state['first_run'] = False

# Define function to fetch the balances of given wallets from the Covalent API for multiple chains

#@st.cache_data
def get_wallets_balances_for_chains(walletAddresses, chains):
    """
    Fetches the balances of given wallets from the Covalent API for multiple chains and returns them as a DataFrame.

    Parameters:
    walletAddresses (list of str): The addresses of the wallets to fetch the balances for.
    chains (list): The list of chains to fetch the balance for.

    Returns:
    df (pd.DataFrame): A DataFrame containing the balance information for the wallets.
    """

    df = pd.DataFrame()

    for walletAddress in walletAddresses:
        for chain in chains:
            # Construct the URL for the API request
            url = f"https://api.covalenthq.com/v1/{chain}/address/{walletAddress}/balances_v2/?quote-currency=USD"

            # Send a GET request to the API
            response = requests.get(url, auth=HTTPBasicAuth(COVALENT_API_KEY, ''))

            # Check if the request was successful
            if response.status_code != 200:
                print(f"Failed to fetch balance for wallet {walletAddress} on chain {chain}: {response.content}")
                continue

            # Parse the JSON response
            data = response.json()

            # Check if the response contains data
            if data['data'] is None:
                print(f"No data for wallet {walletAddress} on chain {chain}")
                continue

            # Convert the relevant part of the JSON response into a DataFrame
            chain_df = pd.DataFrame(data['data']['items'])

            # Add a column to identify the chain
            chain_df['chain'] = chain

            # Add a column to identify the wallet address
            chain_df['walletAddress'] = walletAddress

            # Append the data to the main DataFrame
            df = pd.concat([df, chain_df], ignore_index=True)

    # Return the DataFrame
    return df


# Define list of chains and show sample-default wallets for user input 
cadenas = ['eth-mainnet', 'bsc-mainnet', 'matic-mainnet', 'optimism-mainnet', 'avalanche-mainnet', 'arbitrum-mainnet']
#carteras = ['0xfc43f5f9dd45258b3aff31bdbe6561d97e8b71de', '0xdac17f958d2ee523a2206206994597c13d831ec7']


# Get wallet address and chains from user
wallet_input = st.text_input("**Enter wallets (separated by commas):**", '0xfc43f5f9dd45258b3aff31bdbe6561d97e8b71de , 0xdac17f958d2ee523a2206206994597c13d831ec7') # "0xf8c3527cc04340b208c854e985240c02f7b7793f")
# Parse the wallets from the input
wallets = [wallet.strip() for wallet in wallet_input.split(',')]

chain_names = st.multiselect('**Select Blockchains**', cadenas, 
                             default=cadenas)

if not chain_names:
    st.write("No chain selected.")
    st.stop()

#@st.cache_data
if wallet_input:
    data = get_wallets_balances_for_chains(wallets, chain_names)
    # Create a copy of the DataFrame
    df = data.copy()
    if 'balance' in df.columns:
        df['balance'] = pd.to_numeric(df['balance'], errors='coerce', downcast='float')
    else:
        st.write("No data available for the selected chains.")
    # Convert balance to numeric
    #df['balance'] = pd.to_numeric(df['balance'], errors='coerce', downcast='float')
    # Create a new column for prety_balance = balance/(10^contract_decimals)
    df['pretty_balance'] = df['balance'] / (10 ** df['contract_decimals'])
    # Keep only relevant columns
    df = df[['contract_name', 'contract_ticker_symbol', 'pretty_balance', 'pretty_quote', 'chain', 'logo_url']] # 'chain'
    # Rename columns
    df.columns = ['Name', 'Coin', 'Balance', 'Value', 'Chain', 'Logo',]
    # Remove the dollar sign and commas
    df['Value'] = df['Value'].replace({'\$': '', ',': ''}, regex=True)
    # Convert the column to float using the recommended syntax
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    # Filter out assets with zero or negative balance
    df = df[df['Value'] > 0.00]
    # Sort the values by value
    df = df.sort_values(by='Value', ascending=False)
    # Format the values as dollars
    df['Value'] = df['Value'].apply(lambda x: '${:,.2f}'.format(x))
    # Create a new DataFrame where values less than 100 are grouped into 'Other'
    df_grouped = df.copy()
    df_grouped.loc[df['Value'] < 100, 'Coin'] = 'Other'
    df_grouped = df_grouped.groupby(['Chain', 'Coin']).sum(numeric_only=True).reset_index()
    # Calculate Total Portfolio Value
    total_portfolio_value = df['Value'].sum()
    # Calculate Total Portfolio Value for each chain
    total_portfolio_value_per_chain = df.groupby('Chain')['Value'].sum()

    # Create a pie chart with the total value per chain
    
    # Get the unique chains and calculate the number of rows and columns for the subplots
    unique_chains = df_grouped['Chain'].unique()
    # Check if there are any unique chains
        
    cols = 2  # or however many columns you want
    rows = len(unique_chains) // cols + len(unique_chains) % cols

    # Create color palette from "Paired" seaborn palette
    color_palette = ['#a6cee3', '#1f78b4', '#b2df8a', '#33a02c', '#fb9a99', '#e31a1c', '#fdbf6f', '#ff7f00', '#cab2d6', '#6a3d9a', '#ffff99', '#b15928']
    
    # Create a subplot with 3 rows and 3 columns
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=[f'{chain} = ${value:,.2f}' for chain, value in total_portfolio_value_per_chain.items()], specs=[[{'type': 'domain'}]*cols]*rows)

    # Loop over each unique chain
    for i, chain in enumerate(df_grouped['Chain'].unique(), start=1):
        # Filter the data for the current chain
        chain_data = df_grouped[df_grouped['Chain'] == chain]
        
        # Create the donut chart with the defined color palette
        pie = px.pie(chain_data, values='Value', names='Coin', hole=.3, color_discrete_sequence=color_palette)
        
        # Customize the hovertemplate to show absolute values
        pie.update_traces(textinfo='none', hovertemplate='coin: %{label}<br>value: $%{value}<extra></extra>')
        
        # Add the pie chart to the subplot
        fig.add_trace(pie.data[0], row=(i-1)//cols+1, col=(i-1)%cols+1)

    # Adjust the aspect ratio of the figure
    fig.update_layout(autosize=True, title=f"Total Balance = ${total_portfolio_value:,.2f}", 
                      title_x=0.35, paper_bgcolor='rgb(230, 230, 250)')

    # Show the chart
    #fig.show()

    #Show plot in Streamlit
    st.plotly_chart(fig)



    # Get unique chains and add an "All" option
    chains = list(df['Chain'].unique())
    chains.insert(0, 'Total')

    # Create a selectbox for the chains
    selected_chain = st.selectbox('Select a Chain', chains)

    # Filter the DataFrame based on the selected chain
    if selected_chain != 'Total':
        filtered_df = df[df['Chain'] == selected_chain]
    else:
        filtered_df = df

    st.markdown(f'### Blockchain {selected_chain} Token Balance')
    st.dataframe(filtered_df, column_config={
            "Logo": st.column_config.ImageColumn(
                "Logo", help="Token logo", width='small'
            )
        },
        hide_index=True,)

    
