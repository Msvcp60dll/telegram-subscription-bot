#!/usr/bin/env python3
"""
Utility script to convert various member list formats to migration format
Supports Telegram Desktop exports, CSV files, and other common formats
"""

import json
import csv
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

def parse_telegram_desktop_json(file_path: str) -> List[Dict[str, Any]]:
    """Parse Telegram Desktop JSON export"""
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
        # Nested structure
        if 'members' in data:
            for item in data['members']:
                member = convert_telegram_user(item)
                if member:
                    members.append(member)
        elif 'users' in data:
            for item in data['users']:
                member = convert_telegram_user(item)
                if member:
                    members.append(member)
    
    return members

def convert_telegram_user(user_data: Dict) -> Optional[Dict[str, Any]]:
    """Convert Telegram user data to our format"""
    # Try different field names
    telegram_id = (
        user_data.get('id') or 
        user_data.get('user_id') or 
        user_data.get('telegram_id')
    )
    
    if not telegram_id:
        return None
    
    # Build full name
    first_name = user_data.get('first_name', '')
    last_name = user_data.get('last_name', '')
    full_name = f"{first_name} {last_name}".strip() or user_data.get('name', '')
    
    return {
        'telegram_id': int(telegram_id),
        'username': user_data.get('username'),
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
    """Parse simple JSON array of IDs"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    members = []
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, int):
                # Simple ID
                members.append({
                    'telegram_id': item,
                    'username': None,
                    'full_name': None
                })
            elif isinstance(item, str) and item.isdigit():
                # String ID
                members.append({
                    'telegram_id': int(item),
                    'username': None,
                    'full_name': None
                })
            elif isinstance(item, dict):
                # Try to extract from dict
                member = convert_telegram_user(item)
                if member:
                    members.append(member)
    
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

def validate_members(members: List[Dict[str, Any]]) -> tuple:
    """Validate and clean member list"""
    valid_members = []
    duplicates = []
    invalid = []
    seen_ids = set()
    
    for member in members:
        telegram_id = member.get('telegram_id')
        
        # Validate ID
        if not telegram_id or not isinstance(telegram_id, int):
            invalid.append(member)
            continue
        
        # Check for duplicates
        if telegram_id in seen_ids:
            duplicates.append(member)
            continue
        
        seen_ids.add(telegram_id)
        valid_members.append(member)
    
    return valid_members, duplicates, invalid

def main():
    parser = argparse.ArgumentParser(
        description='Convert member lists to migration format'
    )
    parser.add_argument('input', help='Input file path')
    parser.add_argument('-o', '--output', help='Output file path (default: members_for_migration.json)')
    parser.add_argument('-f', '--format', choices=['auto', 'telegram_json', 'csv', 'txt', 'simple_json'],
                       default='auto', help='Input file format')
    parser.add_argument('--validate', action='store_true', help='Validate and show statistics only')
    parser.add_argument('--merge', nargs='+', help='Merge multiple input files')
    
    args = parser.parse_args()
    
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
            else:
                print(f"Error: Unknown format for {input_file}")
                continue
            
            all_members.extend(members)
            print(f"Parsed {len(members)} members from {input_file}")
            
        except Exception as e:
            print(f"Error parsing {input_file}: {e}")
            sys.exit(1)
    
    # Validate members
    valid_members, duplicates, invalid = validate_members(all_members)
    
    print(f"\nValidation Results:")
    print(f"  Valid members: {len(valid_members)}")
    print(f"  Duplicates removed: {len(duplicates)}")
    print(f"  Invalid entries: {len(invalid)}")
    
    if args.validate:
        # Just show statistics
        print(f"\nSample of valid members:")
        for member in valid_members[:5]:
            print(f"  - ID: {member['telegram_id']}, Username: {member.get('username', 'N/A')}")
        
        if duplicates:
            print(f"\nDuplicate IDs found:")
            for member in duplicates[:5]:
                print(f"  - {member['telegram_id']}")
        
        if invalid:
            print(f"\nInvalid entries:")
            for member in invalid[:5]:
                print(f"  - {member}")
    else:
        # Save to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(valid_members, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Successfully saved {len(valid_members)} members to {output_file}")
        print(f"You can now use this file with the migration tool:")
        print(f"  python migrate_existing_members.py --source file --file {output_file}")

if __name__ == "__main__":
    main()