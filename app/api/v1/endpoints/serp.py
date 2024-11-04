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

router = APIRouter()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a response model
class AIOverviewResponse(BaseModel):
    message: str

# Define a function to handle individual query requests
async def fetch_and_write(query: str, api_key: str, temp_file):
    # SERP API parameters
    params = {
        "q": query,
        "api_key": api_key
    }

    def write_to_file(query: str, ai_overview: dict = None):
        temp_file.write("------------------------Query Begins------------------------\n")
        temp_file.write(f"Keyword:\n {query}\n\n")
        temp_file.write(f"Response:\n")
        
        references = ai_overview.get("references", [])
        references_dict = {ref["index"]: ref for ref in references}

        for block in ai_overview.get("text_blocks", []):
            if block["type"] == "paragraph":
                temp_file.write(f"{block['snippet']}\n\n")
            elif block["type"] == "list":
                for item in block.get("list", []):
                    temp_file.write(f"- {item['title']}: {item['snippet']}\n")
                temp_file.write("\n")

            # Append references for each text block
            if "reference_indexes" in block:
                temp_file.write("References:\n")
                for index in block["reference_indexes"]:
                    ref = references_dict.get(index)
                    if ref:
                        temp_file.write(f"- {ref['title']} ({ref['source']}): {ref['link']}\n")

        temp_file.write("\n------------------------Query Ends------------------------\n\n")

        temp_file.flush()  # Ensure data is written to disk

    try:
        # Use asyncio.to_thread if serpapi.search is synchronous
        results = await asyncio.to_thread(serpapi.search, params)
        print('results=>keys', results)
        ai_overview = results.get("ai_overview")

        if ai_overview is None:
            temp_file.write("------------------------Query Begins------------------------\n")
            temp_file.write(f"Keyword:\n {query}\n\n")
            temp_file.write("No AI overview found, Skipping....\n")
            temp_file.write("\n------------------------Query Ends------------------------\n\n")
        else:
            # Write the query and AI overview to the temporary file
            write_to_file(query, ai_overview)

    except Exception as e:
        error_message = f"An error occurred with query '{query}': {str(e)}\n{traceback.format_exc()}"
        logger.error(error_message)

@router.get("/search", response_model=AIOverviewResponse)
async def search(queries: List[str] = Query(..., description="Array of search query strings")):
    # Ensure the API key is available
    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key for SERP API is not configured.")

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w+') as temp_file:
        # Run each fetch_and_write task concurrently
        tasks = [fetch_and_write(query, api_key, temp_file) for query in queries]
        await asyncio.gather(*tasks)  # Run all tasks concurrently

        # Close the file to flush data and make it ready for download
        temp_file_path = temp_file.name

    # Return the temporary file as a downloadable response
    return FileResponse(temp_file_path, filename="ai_overview.txt", media_type="text/plain")
