import streamlit as st
import requests
from web3 import Web3
import json
from PIL import Image
import io

# ===== SETUP =====
st.set_page_config(page_title="Tx Simulator", page_icon="⛓️")
DUNE_API_URL = "https://api.sim.dune.com/v1/simulate"
CHAIN_IDS = {
    "Ethereum": 1,
    "Polygon": 137,
    "BNB Smart Chain": 56,
    "Arbitrum": 42161,
    "Optimism": 10,
    "Avalanche C-Chain": 43114,
    "Fantom": 250,
    "Celo": 42220,
    "Gnosis (xDAI)": 100,
    "zkSync Era": 324,
    "Base": 8453,
    "Linea": 59144,
    "Polygon zkEVM": 1101,
    "Scroll": 534352,
    "Mantle": 5000,
    "Kava": 2222,
    "Metis": 1088,
    "Moonbeam": 1284,
    "Moonriver": 1285,
    "Harmony": 1666600000,
    "Cronos": 25,
    "Aurora": 1313161554,
}

# ===== UTILS =====
@st.cache_data(ttl=300)
def simulate_tx(api_key, tx_data, chain_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "transaction": {"data": tx_data},
        "chain_id": chain_id
    }
    return requests.post(DUNE_API_URL, headers=headers, json=payload).json()

@st.cache_data
def get_nft_image(api_key, contract_address, token_id):
    response = requests.get(
        f"https://api.sim.dune.com/v1/nft/{contract_address}/{token_id}",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    return None

def decode_abi_if_provided(raw_tx, abi_json):
    if not abi_json:
        return raw_tx
    
    try:
        abi = json.loads(abi_json)
        w3 = Web3()
        contract = w3.eth.contract(abi=abi)
        func_obj, params = contract.decode_function_input(raw_tx)
        return {
            "function": func_obj.fn_name,
            "params": dict(params)
        }
    except Exception as e:
        st.warning(f"ABI decoding failed: {str(e)}")
        return raw_tx

# ===== UI =====
st.title("🔮 Tx Simulator Pro")
st.markdown("Simulate EVM transactions before executing them.")

# Sidebar for API key and chain selection
with st.sidebar:
    st.subheader("Settings")
    api_key = st.text_input("Dune API Key", type="password")
    chain = st.selectbox("Chain", list(CHAIN_IDS.keys()))

# Main input
tab1, tab2 = st.tabs(["Raw Transaction", "ABI Decoder"])

with tab1:
    raw_tx = st.text_area("Hex Data (0x...)", height=100)

with tab2:
    abi_json = st.text_area("Contract ABI (JSON)", height=200)
    if abi_json:
        decoded = decode_abi_if_provided(raw_tx, abi_json)
        if isinstance(decoded, dict):
            st.json(decoded)

# Simulation button
if st.button("🚀 Simulate", disabled=not (api_key and raw_tx)):
    if not raw_tx.startswith("0x"):
        st.error("Transaction data must start with '0x'")
    else:
        with st.spinner("Simulating..."):
            try:
                result = simulate_tx(api_key, raw_tx, CHAIN_IDS[chain])
                
                # Results Section
                st.subheader("📊 Results")
                
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    # Basic Info
                    col1, col2 = st.columns(2)
                    col1.metric("Status", "✅ Success" if result.get("success") else "❌ Reverted")
                    col2.metric("Gas Used", result.get("gas_used", "N/A"))
                    
                    # Balance Changes
                    if "balance_changes" in result:
                        st.subheader("💸 Balance Changes")
                        st.dataframe(result["balance_changes"])
                    
                    # NFT Previews (if any)
                    nft_transfers = result.get("nft_transfers", [])
                    if nft_transfers:
                        st.subheader("🖼️ NFT Transfers")
                        cols = st.columns(3)
                        for i, transfer in enumerate(nft_transfers[:3]):  # Show max 3
                            with cols[i]:
                                img = get_nft_image(
                                    api_key,
                                    transfer["contract_address"],
                                    transfer["token_id"]
                                )
                                if img:
                                    st.image(img, width=100)
                                st.caption(f"Token #{transfer['token_id']}")
                    
                    # Risk Detection
                    risks = []
                    if result.get("gas_used", 0) > 500000:
                        risks.append("⚠️ High gas usage (>500k)")
                    if "approvals" in result:
                        risks.append("🔓 New token approvals detected")
                    
                    if risks:
                        st.subheader("🚨 Risks")
                        for risk in risks:
                            st.warning(risk)
                
            except Exception as e:
                st.error(f"💥 API Error: {str(e)}")

# Footer
st.markdown("---")
st.caption("Uses Dune SIM API | Rate limits apply")
