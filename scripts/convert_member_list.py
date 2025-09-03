#!/usr/bin/env python3
"""
Utility script to convert various member list formats to migration format
Supports Telegram Desktop exports, CSV files, and other common formats
Enhanced with support for multiple export formats and data validation
"""

import json
import csv
import argparse
import sys
import re
import html
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

def parse_telegram_desktop_json(file_path: str) -> List[Dict[str, Any]]:
    """Parse Telegram Desktop JSON export with enhanced format support"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    members = []
    
    # Handle different Telegram export structures
    if isinstance(data, list):
        # Direct member list
        for item in data:
            member = convert_telegram_user(item)
            if member:
                members.append(member)
    elif isinstance(data, dict):
        # Nested structure - check multiple possible keys
        possible_keys = ['members', 'users', 'participants', 'chat_members', 'group_members']
        
        for key in possible_keys:
            if key in data:
                items = data[key]
                if isinstance(items, list):
                    for item in items:
                        member = convert_telegram_user(item)
                        if member:
                            members.append(member)
                break
        
        # Also check for nested chat/group structure
        if 'chat' in data and isinstance(data['chat'], dict):
            if 'members' in data['chat']:
                for item in data['chat']['members']:
                    member = convert_telegram_user(item)
                    if member:
                        members.append(member)
    
    return members

def convert_telegram_user(user_data: Dict) -> Optional[Dict[str, Any]]:
    """Convert Telegram user data to our format with enhanced field detection"""
    # Handle nested user object
    if 'user' in user_data and isinstance(user_data['user'], dict):
        user_data = user_data['user']
    
    # Try different field names for ID
    telegram_id = None
    id_fields = ['id', 'user_id', 'telegram_id', 'from_id', 'peer_id']
    
    for field in id_fields:
        if field in user_data:
            value = user_data[field]
            # Handle nested ID structures
            if isinstance(value, dict) and 'user_id' in value:
                telegram_id = value['user_id']
            elif value:
                telegram_id = value
            if telegram_id:
                break
    
    if not telegram_id:
        return None
    
    # Ensure ID is numeric
    try:
        telegram_id = int(telegram_id)
    except (ValueError, TypeError):
        return None
    
    # Skip bots if indicated
    if user_data.get('is_bot', False) or user_data.get('bot', False):
        return None
    
    # Extract username (remove @ if present)
    username = user_data.get('username') or user_data.get('user_name')
    if username:
        username = username.lstrip('@')
        # Validate username format
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', username):
            username = None
    
    # Build full name from various possible fields
    first_name = html.unescape(str(user_data.get('first_name', '') or ''))
    last_name = html.unescape(str(user_data.get('last_name', '') or ''))
    full_name = f"{first_name} {last_name}".strip()
    
    if not full_name:
        full_name = user_data.get('name') or user_data.get('full_name') or user_data.get('title')
        if full_name:
            full_name = html.unescape(str(full_name))
    
    return {
        'telegram_id': telegram_id,
        'username': username,
        'full_name': full_name if full_name else None
    }

def parse_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse CSV file with member data"""
    members = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Try to find ID field
            telegram_id = None
            for field in ['id', 'telegram_id', 'user_id', 'ID', 'Id']:
                if field in row and row[field]:
                    try:
                        telegram_id = int(row[field])
                        break
                    except ValueError:
                        continue
            
            if not telegram_id:
                continue
            
            # Try to find username
            username = None
            for field in ['username', 'Username', 'user_name', 'handle']:
                if field in row and row[field]:
                    username = row[field].lstrip('@')  # Remove @ if present
                    break
            
            # Try to build full name
            full_name = None
            if 'full_name' in row:
                full_name = row['full_name']
            elif 'name' in row:
                full_name = row['name']
            elif 'first_name' in row or 'last_name' in row:
                first = row.get('first_name', '')
                last = row.get('last_name', '')
                full_name = f"{first} {last}".strip()
            
            members.append({
                'telegram_id': telegram_id,
                'username': username,
                'full_name': full_name if full_name else None
            })
    
    return members

def parse_text_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse text file with IDs (one per line)"""
    members = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Try to parse as ID
            try:
                telegram_id = int(line.split()[0])  # Take first part if space-separated
                members.append({
                    'telegram_id': telegram_id,
                    'username': None,
                    'full_name': None
                })
            except (ValueError, IndexError):
                print(f"Skipping invalid line: {line}")
    
    return members

def parse_simple_json(file_path: str) -> List[Dict[str, Any]]:
    """Parse simple JSON array of IDs or user objects"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    members = []
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, (int, float)):
                # Simple ID
                members.append({
                    'telegram_id': int(item),
                    'username': None,
                    'full_name': None
                })
            elif isinstance(item, str):
                # Could be string ID or username
                if item.isdigit():
                    members.append({
                        'telegram_id': int(item),
                        'username': None,
                        'full_name': None
                    })
                elif item.startswith('@'):
                    # Username only - can't migrate without ID
                    print(f"Warning: Username without ID cannot be migrated: {item}")
            elif isinstance(item, dict):
                # Try to extract from dict
                member = convert_telegram_user(item)
                if member:
                    members.append(member)
    elif isinstance(data, dict):
        # Maybe wrapped in an object
        return parse_telegram_desktop_json(file_path)
    
    return members

def generate_sample_data(count: int = 100) -> List[Dict[str, Any]]:
    """Generate sample data for testing"""
    import random
    import string
    
    members = []
    used_ids = set()
    
    for i in range(count):
        # Generate unique ID
        while True:
            telegram_id = random.randint(100000000, 999999999)
            if telegram_id not in used_ids:
                used_ids.add(telegram_id)
                break
        
        # Generate username (70% chance)
        username = None
        if random.random() < 0.7:
            username = ''.join(random.choices(string.ascii_lowercase, k=8))
        
        # Generate full name (90% chance)
        full_name = None
        if random.random() < 0.9:
            first_names = ['John', 'Jane', 'Alex', 'Maria', 'David', 'Sarah', 'Michael', 'Emma']
            last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller']
            full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        members.append({
            'telegram_id': telegram_id,
            'username': username,
            'full_name': full_name
        })
    
    return members

def parse_html_export(file_path: str) -> List[Dict[str, Any]]:
    """Parse HTML export from Telegram (basic support)"""
    members = []
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("BeautifulSoup4 required for HTML parsing. Install with: pip install beautifulsoup4")
        return members
    
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    # Look for user mentions or member lists
    # This is basic and may need adjustment based on actual HTML structure
    for link in soup.find_all('a', href=re.compile(r'tg://user\?id=\d+')):
        href = link.get('href', '')
        match = re.search(r'id=(\d+)', href)
        if match:
            telegram_id = int(match.group(1))
            username = None
            full_name = link.get_text().strip()
            
            members.append({
                'telegram_id': telegram_id,
                'username': username,
                'full_name': full_name if full_name else None
            })
    
    return members

def auto_detect_format(file_path: str) -> str:
    """Auto-detect file format"""
    path = Path(file_path)
    extension = path.suffix.lower()
    
    if extension == '.csv':
        return 'csv'
    elif extension == '.txt':
        return 'txt'
    elif extension == '.json':
        # Check JSON structure
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], (int, str)):
                    return 'simple_json'
                elif isinstance(data[0], dict):
                    # Check for Telegram-like structure
                    if any(key in data[0] for key in ['id', 'user_id', 'telegram_id']):
                        return 'telegram_json'
            elif isinstance(data, dict):
                if 'members' in data or 'users' in data:
                    return 'telegram_json'
            
            return 'telegram_json'  # Default for JSON
        except:
            return 'unknown'
    
    return 'unknown'

def validate_members(members: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Validate and clean member list with enhanced validation"""
    valid_members = []
    duplicates = []
    invalid = []
    seen_ids = set()
    
    for member in members:
        telegram_id = member.get('telegram_id')
        
        # Validate ID
        if not telegram_id:
            invalid.append({**member, 'error': 'missing_id'})
            continue
        
        if not isinstance(telegram_id, int):
            invalid.append({**member, 'error': 'invalid_id_type'})
            continue
        
        # Validate ID range (Telegram user IDs are positive)
        if telegram_id <= 0:
            invalid.append({**member, 'error': 'invalid_id_range'})
            continue
        
        # Check for system/deleted accounts (IDs below 1000 are usually system)
        if telegram_id < 1000:
            invalid.append({**member, 'error': 'system_account'})
            continue
        
        # Check for duplicates
        if telegram_id in seen_ids:
            duplicates.append(member)
            continue
        
        seen_ids.add(telegram_id)
        
        # Clean data before adding
        cleaned_member = {
            'telegram_id': telegram_id,
            'username': member.get('username'),
            'full_name': member.get('full_name')
        }
        
        # Remove None values for cleaner output
        cleaned_member = {k: v for k, v in cleaned_member.items() if v is not None}
        
        valid_members.append(cleaned_member)
    
    return valid_members, duplicates, invalid

def main():
    parser = argparse.ArgumentParser(
        description='Convert member lists to migration format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Convert Telegram export
  %(prog)s telegram_export.json -o members.json
  
  # Merge multiple files
  %(prog)s file1.json --merge file2.csv file3.txt -o combined.json
  
  # Generate sample data for testing
  %(prog)s --generate-sample 100 -o test_members.json
  
  # Validate without saving
  %(prog)s members.json --validate
        '''
    )
    parser.add_argument('input', nargs='?', help='Input file path')
    parser.add_argument('-o', '--output', help='Output file path (default: members_for_migration.json)')
    parser.add_argument('-f', '--format', choices=['auto', 'telegram_json', 'csv', 'txt', 'simple_json', 'html'],
                       default='auto', help='Input file format')
    parser.add_argument('--validate', action='store_true', help='Validate and show statistics only')
    parser.add_argument('--merge', nargs='+', help='Merge multiple input files')
    parser.add_argument('--generate-sample', type=int, metavar='COUNT',
                       help='Generate sample data with COUNT members for testing')
    parser.add_argument('--deduplicate', action='store_true', 
                       help='Remove duplicates across merged files')
    parser.add_argument('--min-info', action='store_true',
                       help='Only include members with at least username or full name')
    parser.add_argument('--stats', action='store_true',
                       help='Show detailed statistics about the data')
    
    args = parser.parse_args()
    
    # Handle sample data generation
    if args.generate_sample:
        print(f"Generating {args.generate_sample} sample members...")
        sample_members = generate_sample_data(args.generate_sample)
        output_file = args.output or 'sample_members.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sample_members, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Generated {len(sample_members)} sample members in {output_file}")
        sys.exit(0)
    
    # Require input file if not generating samples
    if not args.input:
        parser.error("Input file is required (unless using --generate-sample)")
    
    # Determine output file
    output_file = args.output or 'members_for_migration.json'
    
    # Process input files
    all_members = []
    
    input_files = [args.input]
    if args.merge:
        input_files.extend(args.merge)
    
    for input_file in input_files:
        if not Path(input_file).exists():
            print(f"Error: File not found: {input_file}")
            sys.exit(1)
        
        # Detect or use specified format
        if args.format == 'auto':
            format_type = auto_detect_format(input_file)
            print(f"Auto-detected format for {input_file}: {format_type}")
        else:
            format_type = args.format
        
        # Parse based on format
        try:
            if format_type == 'telegram_json':
                members = parse_telegram_desktop_json(input_file)
            elif format_type == 'csv':
                members = parse_csv_file(input_file)
            elif format_type == 'txt':
                members = parse_text_file(input_file)
            elif format_type == 'simple_json':
                members = parse_simple_json(input_file)
            elif format_type == 'html':
                members = parse_html_export(input_file)
            else:
                print(f"Error: Unknown format for {input_file}")
                continue
            
            all_members.extend(members)
            print(f"Parsed {len(members)} members from {input_file}")
            
        except Exception as e:
            print(f"Error parsing {input_file}: {e}")
            sys.exit(1)
    
    # Apply filters if requested
    if args.min_info:
        filtered = []
        for member in all_members:
            if member.get('username') or member.get('full_name'):
                filtered.append(member)
        print(f"Filtered {len(all_members) - len(filtered)} members with insufficient information")
        all_members = filtered
    
    # Validate members
    valid_members, duplicates, invalid = validate_members(all_members)
    
    print(f"\n" + "=" * 60)
    print(f"VALIDATION RESULTS")
    print(f"=" * 60)
    print(f"  Total input records: {len(all_members)}")
    print(f"  Valid members: {len(valid_members)}")
    print(f"  Duplicates removed: {len(duplicates)}")
    print(f"  Invalid entries: {len(invalid)}")
    
    if args.stats or args.validate:
        # Detailed statistics
        with_username = sum(1 for m in valid_members if m.get('username'))
        with_fullname = sum(1 for m in valid_members if m.get('full_name'))
        with_both = sum(1 for m in valid_members if m.get('username') and m.get('full_name'))
        
        print(f"\nData Completeness:")
        print(f"  With username: {with_username} ({with_username/len(valid_members)*100:.1f}%)")
        print(f"  With full name: {with_fullname} ({with_fullname/len(valid_members)*100:.1f}%)")
        print(f"  With both: {with_both} ({with_both/len(valid_members)*100:.1f}%)")
        
        if invalid:
            print(f"\nInvalid Entry Reasons:")
            error_counts = {}
            for item in invalid:
                error = item.get('error', 'unknown')
                error_counts[error] = error_counts.get(error, 0) + 1
            for error, count in error_counts.items():
                print(f"  {error}: {count}")
    
    if args.validate:
        # Just show statistics
        print(f"\nSample of valid members:")
        for member in valid_members[:5]:
            print(f"  - ID: {member['telegram_id']}, Username: {member.get('username', 'N/A')}")
        
        if duplicates:
            print(f"\nDuplicate IDs found:")
            for member in duplicates[:5]:
                print(f"  - {member['telegram_id']}")
        
        if invalid and len(invalid) <= 10:
            print(f"\nInvalid entries:")
            for member in invalid:
                print(f"  - {member}")
    else:
        # Save to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(valid_members, f, indent=2, ensure_ascii=False)
        
        # Also save a summary report
        report_file = output_file.replace('.json', '_report.txt')
        with open(report_file, 'w') as f:
            f.write(f"Migration Data Report\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"="*60 + "\n\n")
            f.write(f"Total valid members: {len(valid_members)}\n")
            f.write(f"Duplicates removed: {len(duplicates)}\n")
            f.write(f"Invalid entries: {len(invalid)}\n")
            f.write(f"\nOutput file: {output_file}\n")
            
            if duplicates:
                f.write(f"\nDuplicate IDs (first 10):\n")
                for dup in duplicates[:10]:
                    f.write(f"  - {dup.get('telegram_id')}\n")
        
        print(f"\n✅ Successfully saved {len(valid_members)} members to {output_file}")
        print(f"📊 Report saved to {report_file}")
        print(f"\nNext steps:")
        print(f"  1. Review the report: cat {report_file}")
        print(f"  2. Run migration: python production_migration.py --file {output_file}")
        print(f"  3. Or dry run first: python production_migration.py --file {output_file} --dry-run")

if __name__ == "__main__":
    main()