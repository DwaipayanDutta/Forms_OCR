import ollama
from PIL import Image
import base64
import io
from pdf2image import convert_from_path
import json
from datetime import datetime
import plotly.graph_objects as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State


def document_to_base64(document_path):
    if document_path.lower().endswith('.pdf'):
        return encode_pdf_to_base64(document_path)
    else:
        return encode_image_to_base64(document_path)


def encode_pdf_to_base64(pdf_path):
    images = convert_from_path(pdf_path)
    base64_encoded_images = []

    for img in images:
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        base64_encoded_images.append(img_base64)

    return base64_encoded_images


def encode_image_to_base64(image_path):
    with Image.open(image_path) as img:
        buffered = io.BytesIO()
        img.save(buffered, format=img.format)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')


def extract_pan_details(base64_image):

    try:
        response = ollama.chat(
            model="llama3.2-vision:latest",
            messages=[{
                "role": "user",
                "content": "The image is an Indian PAN Card. Output should be in this format - <Name of the PAN Card Holder>, <Father's Name>, <PAN Number>, <Date of Birth>. Do not output anything else.",
                "images": [base64_image]
            }],
        )

        response_text = response['message']['content'].strip()

        pan_details = response_text.split(',')

        if len(pan_details) != 4:
            return None  # Indicate extraction failure

        return {
            "Name": pan_details[0].strip(),
            "Father's Name": pan_details[1].strip(),
            "PAN NO": pan_details[2].strip(),
            "DOB": pan_details[3].strip()
        }
    except Exception as e:
        print(f"Error during PAN details extraction: {e}")
        return None


def save_json_response(pan_dict):
    """Saves the PAN details to a JSON file with a timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pan_details_{timestamp}.json"
    try:
        with open(filename, 'w') as f:
            json.dump(pan_dict, f, indent=4)
        print(f"PAN details saved to {filename}")
    except Exception as e:
        print(f"Error saving JSON response: {e}")


# Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("PAN Card Information Extractor"),
    dcc.Upload(
        id='upload-image',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select an Image/PDF')
        ]),
        style={
            'width': '90%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False  # Allow only one file to be uploaded
    ),
    html.Div(id='output-image-upload'),
    html.Div(id='output-pan-details'),
])


def parse_contents(contents, filename):
    """Parses the uploaded file content and displays the image."""
    return html.Div([
        html.H5(filename),
        html.Img(src=contents, style={'width': '50%'}),
        html.Hr(),
        html.H6("Extracted Details:"),
        html.Div(id='pan-details-output'),  # Placeholder for PAN details
    ])


@app.callback(Output('output-image-upload', 'children'),
              [Input('upload-image', 'contents')],
              [State('upload-image', 'filename')])
def update_output(contents, filename):
    """Updates the output with the uploaded image."""
    if contents:
        return parse_contents(contents, filename)
    return ''


@app.callback(
    Output('pan-details-output', 'children'),
    [Input('upload-image', 'contents')]
)
def display_pan_details(contents):
    """Extracts and displays PAN card details."""
    if contents is not None:
        try:
            # Extract the data and the filename from the contents
            content_type, content_string = contents.split(',')
            # Decode the image
            decoded = base64.b64decode(content_string)
            image = Image.open(io.BytesIO(decoded))
            # Convert the image to base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")  # Change format if needed
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

            pan_dict = extract_pan_details(img_str)

            if pan_dict:
                save_json_response(pan_dict)
                return html.Div([
                    html.P(f"Name: {pan_dict['Name']}"),
                    html.P(f"Father's Name: {pan_dict['Father\'s Name']}"),
                    html.P(f"PAN NO: {pan_dict['PAN NO']}"),
                    html.P(f"DOB: {pan_dict['DOB']}")
                ])
            else:
                return html.Div([
                    html.P("Could not extract PAN details. Please ensure the image is clear and try again.")
                ])
        except Exception as e:
            print(e)
            return html.Div([
                html.P("There was an error processing the file.")
            ])
    return ''


if __name__ == '__main__':
    app.run(debug=True)
