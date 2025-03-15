import os
import re
import csv
import argparse
import pandas as pd
from tqdm import tqdm
from urllib.parse import urlparse

def extract_metadata(text):
    """Extract source URL and domain from the file metadata."""
    source_url = None
    domain = None
    
    # Look for source URL in the metadata section
    match = re.search(r'Source URL: (https?://[^\n]+)', text)
    if match:
        source_url = match.group(1)
        domain = urlparse(source_url).netloc
        
    return source_url, domain

def extract_company_name(domain):
    """Extract company name from domain."""
    if not domain:
        return "Unknown"
        
    # Remove common TLDs and www
    company = domain.lower()
    company = re.sub(r'^www\.', '', company)
    company = re.sub(r'\.(com|org|net|io|co|gov|edu)(\.[a-z]{2})?$', '', company)
    
    # Special cases for multi-part domains
    if 'thalesgroup' in company:
        return 'Thales'
    if 'samsungsds' in company:
        return 'Samsung SDS'
    if 'qnulabs' in company:
        return 'QNU Labs'
    if 'quantumxc' in company:
        return 'QuantumXC'
    if 'qusecure' in company:
        return 'QuSecure'
    if 'cryptoquantique' in company:
        return 'CryptoQuantique'
    if 'crypto4a' in company:
        return 'Crypto4A'
        
    # Return capitalized company name
    parts = company.split('.')
    return parts[0].capitalize()

def main():
    parser = argparse.ArgumentParser(description='Combine text files for Orange analysis')
    parser.add_argument('--input_dir', type=str, default='/Users/joehu/Downloads/pqc_companies_corpus',
                      help='Directory containing the scraped text files')
    parser.add_argument('--output_dir', type=str, default='/Users/joehu/Downloads',
                      help='Directory to save the combined outputs')
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Output file paths
    combined_txt_path = os.path.join(args.output_dir, 'pqc_combined_corpus.txt')
    csv_path = os.path.join(args.output_dir, 'pqc_documents.csv')
    tab_path = os.path.join(args.output_dir, 'pqc_documents.tab')  # Orange's preferred format
    excel_path = os.path.join(args.output_dir, 'pqc_documents.xlsx')
    
    # Get list of all txt files
    txt_files = [f for f in os.listdir(args.input_dir) if f.endswith('.txt') and f != 'scrape_summary.txt']
    
    print(f"Found {len(txt_files)} text files to process")
    
    # Prepare data structures
    all_texts = []
    documents_data = []
    
    # Process each text file
    for filename in tqdm(txt_files, desc="Processing files"):
        file_path = os.path.join(args.input_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract metadata (first few lines)
            source_url, domain = extract_metadata(content)
            
            # Skip metadata lines to get just the content
            content_parts = content.split("-" * 80 + "\n\n", 1)
            if len(content_parts) > 1:
                text_content = content_parts[1]
            else:
                text_content = content
                
            # Extract document title (use first line of content as title)
            title_lines = [line for line in text_content.split('\n') if line.strip()]
            title = title_lines[0] if title_lines else filename
            
            # Truncate title if too long
            if len(title) > 100:
                title = title[:97] + "..."
                
            # Get company name
            company = extract_company_name(domain)
            
            # Add to all texts (for combined corpus)
            all_texts.append(text_content)
            
            # Add to documents data (for metadata CSV)
            documents_data.append({
                'filename': filename,
                'title': title,
                'company': company,
                'domain': domain,
                'source_url': source_url,
                'content_length': len(text_content),
                'content': text_content
            })
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    # Create combined text corpus (useful for some analysis)
    with open(combined_txt_path, 'w', encoding='utf-8') as f:
        f.write("\n\n===== NEW DOCUMENT =====\n\n".join(all_texts))
    
    print(f"Combined corpus saved to {combined_txt_path}")
    
    # Create pandas DataFrame
    df = pd.DataFrame(documents_data)
    
    # Save as CSV
    df.to_csv(csv_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"CSV metadata file saved to {csv_path}")
    
    # Save as Excel
    df.to_excel(excel_path, index=False)
    print(f"Excel file saved to {excel_path}")
    
    # Save as Orange .tab format (tab-delimited with special header)
    # Orange expects a specific format for .tab files
    with open(tab_path, 'w', encoding='utf-8') as f:
        # Write variable names (column headers)
        f.write('\t'.join(['filename', 'title', 'company', 'domain', 'source_url', 'content_length', 'content']) + '\n')
        
        # Write variable types (Orange specific)
        f.write('\t'.join(['string', 'string', 'string', 'string', 'string', 'continuous', 'string']) + '\n')
        
        # Write meta attributes (m for meta, c for class, blank for regular)
        f.write('\t'.join(['m', 'm', 'm', 'm', 'm', 'm', '']) + '\n')
        
        # Write data rows
        for _, row in df.iterrows():
            values = [
                str(row['filename']).replace('\t', ' '),
                str(row['title']).replace('\t', ' '),
                str(row['company']).replace('\t', ' '),
                str(row['domain']).replace('\t', ' '),
                str(row['source_url']).replace('\t', ' '),
                str(row['content_length']),
                str(row['content']).replace('\t', ' ')
            ]
            f.write('\t'.join(values) + '\n')
    
    print(f"Orange tab file saved to {tab_path}")
    
    # Print summary stats
    company_counts = df['company'].value_counts()
    print("\nDocument count by company:")
    for company, count in company_counts.items():
        print(f"  {company}: {count} documents")

if __name__ == "__main__":
    main()