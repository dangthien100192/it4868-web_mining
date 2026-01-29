import gradio as gr
from recommend import Recommender
import pandas as pd

# Load Recommender once
print("Initializing Recommender System...")
rec = Recommender()
print("System Ready.")

def get_recs(user_id):
    if not user_id:
        return pd.DataFrame()
    
    # Get recommendations
    results = rec.recommend(user_id, top_k=15)
    
    # Format as DataFrame for friendly display
    if not results:
        # Return empty dataframe with headers
        return pd.DataFrame(columns=["item_id"])
        
    if isinstance(results[0], str): # Handle error messages if any
         # Wrap error in dataframe
         return pd.DataFrame([{"Error": results[0]}])
         
    df = pd.DataFrame(results)
    # Ensure columns order if possible
    cols = ['item_id', 'score', 'reason', 'source']
    # Filter to only existing cols (in case of error dict)
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    return df

# UI Definition
with gr.Blocks(title="User-User Recommendation System") as demo:
    gr.Markdown("# User-User Recommendation System (Similarity)")
    gr.Markdown("Enter a User ID to get personalized product recommendations based on similar users.")
    
    with gr.Row():
        user_input = gr.Textbox(label="User ID (IP Address)", placeholder="e.g. 113.160.204.52")
        submit_btn = gr.Button("Get Recommendations", variant="primary")
        
    output_table = gr.Dataframe(label="Recommended Items", headers=["item_id", "score", "reason", "source"])
    
    submit_btn.click(fn=get_recs, inputs=user_input, outputs=output_table)
    
    # Add examples
    gr.Examples(
        examples=[
            ["57.141.12.38"], 
            ["173.252.82.13"],
            ["103.17.88.103"],
            ["171.240.129.207"]
        ],
        inputs=user_input
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=8988)
