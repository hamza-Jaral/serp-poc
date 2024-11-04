from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import os
import serpapi
import asyncio
import traceback
import logging
import tempfile
import requests
from bs4 import BeautifulSoup

router = APIRouter()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a response model
class AIOverviewResponse(BaseModel):
    message: str

# Define a function for merging Google results and extracted elements
def process_google_results(result):
    # Extract search metadata, ai_overview, and references from the result
    search_metadata = result.get("search_metadata", {})
    ai_overview = result.get("ai_overview", {})
    references = result.get("references", [])

    # Build a dictionary of references for quick lookup by index
    references_dict = {ref["index"]: ref for ref in references}

    # Download the HTML content directly from the raw_html_file URL
    raw_html_url = search_metadata.get("raw_html_file")
    html_content = ""
    if raw_html_url:
        response = requests.get(raw_html_url)
        if response.status_code == 200:
            html_content = response.text
        else:
            print("Failed to download the HTML file:", response.status_code)

    # Parse the HTML content to extract elements
    soup = BeautifulSoup(html_content, "html.parser")
    data_elements = soup.find_all(attrs={"data-al": True}) + soup.find_all(attrs={"data-aquarium": True})

    # Extract "WaaZC" elements as structured objects
    extracted_elements = []
    for element in data_elements:
        waaZC_elements = element.find_all(class_="WaaZC")
        
        for waaZC_element in waaZC_elements:
            # Determine if it's a list or paragraph and structure accordingly
            if waaZC_element.find("ul") or waaZC_element.find("ol"):
                list_items = waaZC_element.find_all("li")
                list_obj = {
                    "type": "list",
                    "list": [{"snippet": item.get_text(strip=True)} for item in list_items]
                }
                extracted_elements.append(list_obj)
            else:
                paragraph_obj = {
                    "type": "paragraph",
                    "snippet": waaZC_element.get_text(strip=True)
                }
                extracted_elements.append(paragraph_obj)

    # Merge ai_overview with extracted_elements, filling missing properties and adding references
    merged_list = []
    for i, ai_item in enumerate(ai_overview.get("text_blocks", [])):
        merged_item = ai_item.copy()  # Start with ai_overview item

        # Fill missing properties from extracted_elements based on type
        if ai_item.get("type") == "paragraph":
            if "snippet" not in merged_item and i < len(extracted_elements) and extracted_elements[i].get("snippet"):
                merged_item["snippet"] = extracted_elements[i]["snippet"]
        elif ai_item.get("type") == "list":
            if "list" not in merged_item and i < len(extracted_elements) and extracted_elements[i].get("list"):
                merged_item["list"] = extracted_elements[i]["list"]


        # Retain items with 'reference_indexes' or filled properties
        if "reference_indexes" in ai_item or "snippet" in merged_item or "list" in merged_item:
            merged_list.append(merged_item)

    return merged_list

# Define a function to handle individual query requests
async def fetch_and_write(query: str, api_key: str, temp_file):
    params = {
        "q": query,
        "api_key": api_key
    }

    def write_to_file(query: str, merged_list: List[dict], results):
        # Build a references dictionary for quick lookup
        references = results.get("ai_overview", {}).get("references", [])
        references_dict = {ref["index"]: ref for ref in references}

        temp_file.write("------------------------Query Begins------------------------\n")
        temp_file.write(f"Keyword:\n {query}\n\n")
        temp_file.write("Response:\n")

        for block in merged_list:
            # Write paragraph or list
            if block["type"] == "paragraph":
                temp_file.write(f"Paragraph:\n{block['snippet']}\n\n")
            elif block["type"] == "list":
                temp_file.write("List:\n")
                for item in block.get("list", []):
                    temp_file.write(f"- {item.get('snippet')}\n")
                temp_file.write("\n")

            # Write references if reference_indexes exist
            if "reference_indexes" in block:
                temp_file.write("References:\n")
                for index in block["reference_indexes"]:
                    ref = references_dict.get(index)
                    if ref:
                        temp_file.write(f"- {ref['title']} ({ref['source']}): {ref['link']}\n")
                temp_file.write("-------------------\n")

        temp_file.write("\n------------------------Query Ends------------------------\n\n")
        temp_file.flush()

    try:
        # Use asyncio.to_thread if serpapi.search is synchronous
        results = await asyncio.to_thread(serpapi.search, params)
        
        # Process results to get merged list
        merged_list = process_google_results(results)

        if not merged_list:
            temp_file.write("------------------------Query Begins------------------------\n")
            temp_file.write(f"Keyword:\n {query}\n\n")
            temp_file.write("No AI overview found or processed, Skipping....\n")
            temp_file.write("\n------------------------Query Ends------------------------\n\n")
        else:
            write_to_file(query, merged_list, results)

    except Exception as e:
        error_message = f"An error occurred with query '{query}': {str(e)}\n{traceback.format_exc()}"
        logger.error(error_message)

@router.get("/search", response_model=AIOverviewResponse)
async def search(queries: List[str] = Query(..., description="Array of search query strings")):
    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key for SERP API is not configured.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w+') as temp_file:
        tasks = [fetch_and_write(query, api_key, temp_file) for query in queries]
        await asyncio.gather(*tasks)

        temp_file_path = temp_file.name

    return FileResponse(temp_file_path, filename="ai_overview.txt", media_type="text/plain")
