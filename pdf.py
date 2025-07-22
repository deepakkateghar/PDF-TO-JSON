import fitz  # PyMuPDF
import json
import os
import re

def extract_pdf_content(pdf_path, output_directory):
    """
    Extracts complete questions, options, answers, and images from a PDF.
    """
    os.makedirs(output_directory, exist_ok=True)
    doc = fitz.open(pdf_path)
    extracted_data = []
    image_counter = 0
    
    current_section = ""
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        image_list = page.get_images(full=True)  # Get full image details
        
        # Save all images from the page
        page_images = []
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_ext = base_image["ext"]
            image_path = os.path.join(output_directory, f"page{page_num}_img{image_counter}.{image_ext}")
            
            with open(image_path, "wb") as f:
                f.write(base_image["image"])
            
            page_images.append({
                "path": image_path,
                "bbox": img[1:5]  # (x0, y0, x1, y1)
            })
            image_counter += 1
        
        # Process text content
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Detect section headers
            if line.startswith("SECTION-"):
                current_section = line.split("SECTION-")[1].split()[0]
                i += 1
                continue
                
            # Detect question numbers (like "1.", "2.", etc.)
            if re.match(r'^\d+\.', line):
                question = {
                    "section": current_section,
                    "question_number": int(line.split('.')[0]),
                    "question_text": line.split('.', 1)[1].strip(),
                    "options": {},
                    "answer": None,
                    "question_images": [],
                    "option_images": []
                }
                
                # Collect multi-line question text
                j = i + 1
                while (j < len(lines) and 
                       not re.match(r'^\d+\.', lines[j]) and 
                       not re.match(r'^[A-D]\]', lines[j]) and
                       not lines[j].startswith("Ans")):
                    question["question_text"] += " " + lines[j]
                    j += 1
                
                # Collect options
                while j < len(lines) and re.match(r'^[A-D]\]', lines[j]):
                    option_key = lines[j][0]
                    option_text = lines[j][2:].strip()
                    question["options"][option_key] = {
                        "text": option_text,
                        "image": None
                    }
                    j += 1
                
                # Find answer
                if j < len(lines) and lines[j].startswith("Ans"):
                    answer_match = re.search(r'\[([A-D])\]', lines[j])
                    if answer_match:
                        question["answer"] = answer_match.group(1)
                    j += 1
                
                # Assign images to question or options based on position
                if page_images:
                    # Assign the first image to the question if no options
                    if len(question["options"]) == 0:
                        question["question_images"].append(page_images.pop(0)["path"])
                    else:
                        # Assign images to options
                        for opt in question["options"]:
                            if page_images:
                                question["options"][opt]["image"] = page_images.pop(0)["path"]
                
                # Prepare the option images list
                question["option_images"] = [opt["image"] for opt in question["options"].values() if opt["image"]]
                
                extracted_data.append(question)
                i = j
            else:
                i += 1
    
    return extracted_data

def save_structured_output(data, output_file):
    """Convert to the requested JSON format"""
    formatted_data = []
    for item in data:
        formatted_item = {
            "question": f"{item['question_number']}. {item['question_text']}",
            "images": item["question_images"][0] if item["question_images"] else "",  # Single image path
            "option_images": item["option_images"]  # List of option images
        }
        formatted_data.append(formatted_item)
    
    with open(output_file, "w") as f:
        json.dump(formatted_data, f, indent=2)

def main():
    pdf_file = "data.pdf"
    output_dir = "extracted_images"
    output_json = "output.json"
    
    if not os.path.exists(pdf_file):
        print(f"Error: PDF file not found at {os.path.abspath(pdf_file)}")
        return
    
    print("Extracting content from PDF...")
    extracted_data = extract_pdf_content(pdf_file, output_dir)
    save_structured_output(extracted_data, output_json)
    
    print(f"Successfully extracted {len(extracted_data)} questions")
    print(f"JSON output saved to {output_json}")
    print(f"Images saved to {output_dir}")

if __name__ == "__main__":
    main()
