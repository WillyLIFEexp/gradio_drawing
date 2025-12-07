from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List
from fastapi import Query

import gradio as gr
import plotly.express as px
import pandas as pd
import random
import time
import os
import base64


app = FastAPI()
df_raw = px.data.tips()
all_days = sorted(df_raw['day'].unique().tolist())
all_sexes = sorted(df_raw['sex'].unique().tolist())

os.makedirs("temp_plots", exist_ok=True)
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/api/chart", response_class=HTMLResponse)
def get_chart(
    days: List[str] = Query(default=all_days), 
    sexes: List[str] = Query(default=all_sexes)
):
    if not days or not sexes:
        return "<div>Please select at least one filter.</div>"

    filtered_df = df_raw[
        (df_raw['day'].isin(days)) & 
        (df_raw['sex'].isin(sexes))
    ]
    
    if filtered_df.empty:
         return "<div>No data matches your filters.</div>"
         
    agg_df = filtered_df.groupby(['day', 'sex'], as_index=False)['total_bill'].sum()

    fig = px.bar(
        agg_df, 
        x="day", 
        y="total_bill", 
        color="sex", 
        barmode='group',
        title="Filtered Revenue (FastAPI + Plotly)"
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

@app.get("/api/chart_a", response_class=JSONResponse)
def get_chart(
    days: List[str] = Query(default=all_days), 
    sexes: List[str] = Query(default=all_sexes)
):
    # 1. Validation
    if not days or not sexes:
        return {"error": "Please select at least one filter."}

    filtered_df = df_raw[
        (df_raw['day'].isin(days)) & 
        (df_raw['sex'].isin(sexes))
    ]
    
    if filtered_df.empty:
         return {"error": "No data matches your filters."}
         
    agg_df = filtered_df.groupby(['day', 'sex'], as_index=False)['total_bill'].sum()

    # 2. Create Figure
    fig = px.bar(
        agg_df, x="day", y="total_bill", color="sex", barmode='group',
        title="Revenue"
    )
    
    # 3. Generate HTML String (Interactive)
    # full_html=False allows us to embed it in a div easily
    chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # 4. Generate Image Bytes -> Base64 String (Static)
    # 'to_image' returns raw bytes; we must encode them to string for JSON
    img_bytes = fig.to_image(format="png", width=800, height=400, scale=2)
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    # 5. Return Both
    return {
        "html_content": chart_html,
        "image_base64": img_base64
    }

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <body>
            <h1>FastAPI Multi-Bot Hub</h1>
            <ul>
                <li><a href="/normal">Go to Instant Bot</a></li>
                <li><a href="/stream">Go to Streaming Bot</a></li>
            </ul>
        </body>
    </html>
    """

@app.get('/api/data')
def read_data():
    return {"data": 123}

def echo_bot(msg, his):
    return f"You said {msg}"

def stream_echo(msg, his):
    # 'yield' sends parts of the message one by one
    response_text = f"Streaming Reply: {msg}"
    partial_message = ""
    
    for character in response_text:
        partial_message += character
        time.sleep(0.05)  # Simulate processing time
        yield partial_message

@app.get("/index_two", response_class=HTMLResponse)
def dashboard():
    # We dynamically generate checkboxes based on available data
    day_checkboxes = "".join(
        [f'<label><input type="checkbox" name="day" value="{d}" checked> {d}</label> ' for d in all_days]
    )
    sex_checkboxes = "".join(
        [f'<label><input type="checkbox" name="sex" value="{s}" checked> {s}</label> ' for s in all_sexes]
    )

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI Plotly Dashboard</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            .controls {{ background: #f4f4f4; padding: 15px; margin-bottom: 20px; border-radius: 8px; }}
            label {{ margin-right: 15px; cursor: pointer; }}
            #chart-container {{ border: 1px solid #ddd; min-height: 400px; padding: 10px; }}
        </style>
        </head>
    <body>
        <h1>FastAPI + Plotly (No Gradio)</h1>
        
        <div class="controls" id="filter-form">
            <h3>Filters</h3>
            <div><strong>Days:</strong> {day_checkboxes}</div>
            <div style="margin-top:10px;"><strong>Sex:</strong> {sex_checkboxes}</div>
            <br>
            <button onclick="updateChart()">Update Chart</button>
        </div>

        <div id="chart-container">
            Loading chart...
        </div>

        <script>
            async function updateChart() {{
                // 1. Gather values from checkboxes
                const days = Array.from(document.querySelectorAll('input[name="day"]:checked')).map(cb => cb.value);
                const sexes = Array.from(document.querySelectorAll('input[name="sex"]:checked')).map(cb => cb.value);
                
                // 2. Build Query String (e.g., ?days=Sun&days=Sat&sexes=Male)
                const params = new URLSearchParams();
                days.forEach(d => params.append("days", d));
                sexes.forEach(s => params.append("sexes", s));
                
                // 3. Fetch HTML from FastAPI
                const response = await fetch(`/api/chart?${{params.toString()}}`);
                const html = await response.text();
                
                // 4. Inject HTML into container
                const container = document.getElementById("chart-container");
                container.innerHTML = html;
                
                // 5. Re-execute scripts (Plotly needs to run its JS to render)
                // Browsers often block <script> tags inserted via innerHTML for security.
                // We must manually execute them.
                Array.from(container.querySelectorAll("script")).forEach(oldScript => {{
                    const newScript = document.createElement("script");
                    Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
                    newScript.appendChild(document.createTextNode(oldScript.innerHTML));
                    oldScript.parentNode.replaceChild(newScript, oldScript);
                }});
            }}

            // Initial Load
            updateChart();
        </script>
    </body>
    </html>
    """
    return html_content



stream_demo = gr.ChatInterface(
    fn=stream_echo,
    title="Stream echo"
)

demo = gr.ChatInterface(
    fn=echo_bot,
    title="Test APP",
)

app = gr.mount_gradio_app(app, demo, path='/studio')
app = gr.mount_gradio_app(app, stream_demo, path='/stream')

# [{'role': 'user', 'metadata': None, 'content': [{'text': 'hid', 'type': 'text'}], 'options': None}, {'role': 'assistent', 'metadata': None, 'content': [{'text': 'You said hid', 'type': 'text'}], 'options': None}, {'role': 'user', 'content': 'plot'}, {'role': 'assistent', 'content': <gradio.components.plot.Plot object at 0x000001DC9D5143B0>}]

