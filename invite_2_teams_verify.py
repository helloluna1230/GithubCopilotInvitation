import csv
import json
import requests
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    filename='invite.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Get token from environment variable for better security
token = os.environ.get("GITHUB_TOKEN")
if not token:
    logging.error("GitHub token not found. Set the GITHUB_TOKEN environment variable.")
    print("错误: GitHub token not found. Set the GITHUB_TOKEN environment variable.")
    sys.exit(1)

def invite_user_to_team(organization_name, team_name, username):
    """
    Invite a user to a team using their GitHub username.
    """
    # 检查团队是否存在
    team_id = get_team_id(organization_name, team_name)
    if team_id is None:
        msg = f"团队 {team_name} 在组织 {organization_name} 中不存在，跳过邀请用户 {username}"
        print(f"警告: {msg}")
        logging.warning(msg)
        return {"message": "Team not found", "skipped": True}
        
    url = f'https://api.github.com/orgs/{organization_name}/teams/{team_name}/memberships/{username}'
    headers = {'Authorization': f'token {token}'}
    data = {'role': 'member'}
    response = requests.put(url, headers=headers, data=json.dumps(data))
    
    if response.status_code >= 400:
        logging.error(f"API Response for inviting user {username} to team {team_name}: {response.status_code} - {response.text}")
    else:
        logging.info(f"API Response for inviting user {username} to team {team_name}: {response.status_code} - {response.text}")  
        
    return response.json()


def batch_invite_users_to_teams(organization_name, csv_file):
    """
    Process a CSV file to invite multiple users to teams.
    """
    # Check if file exists
    if not os.path.exists(csv_file):
        logging.error(f"CSV file not found: {csv_file}")
        print(f"错误: CSV file not found: {csv_file}")
        return

    # Read all rows into memory
    rows = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                logging.error(f"CSV file is empty or has invalid format: {csv_file}")
                return
                
            fieldnames = list(reader.fieldnames)
            if 'State' not in fieldnames:
                fieldnames.append('State')
            
            current_team = None
            for row in reader:
                rows.append(row)
                team = row.get('Team', '')
                account = row.get('Account', '')
                state = row.get('State', '')
                
                if team:
                    current_team = team
                if not account:
                    continue
                    
                # Skip if already Active
                if row.get('State') == 'Active':
                    msg = f'跳过已激活用户 {account}'
                    print(msg)
                    logging.info(msg)
                    continue

                msg = f'处理用户 {account} 到团队 {current_team}'
                print(msg)
                logging.info(msg)
                try:
                    if '@' in account:
                        response = invite_user_by_email_to_team(
                            organization_name, current_team, account)
                    else:
                        response = invite_user_to_team(
                            organization_name, current_team, account
                        )
                                                
                    if not response:
                        row['State'] = 'Error:API failure'
                        continue
                    
                    # 检查团队是否存在，如果不存在则跳过
                    if response.get('skipped') and response.get('message') == 'Team not found':
                        row['State'] = 'Skipped:Team not found'
                        msg = f'跳过邀请用户 {account}，因为团队 {current_team} 不存在'
                        print(msg)
                        logging.warning(msg)
                        continue
                    
                    # Check for validation failure first
                    if response.get('message') == 'Validation Failed' and \
                       any(error.get('message') == 'A user with this email address is already a part of this organization' 
                           for error in response.get('errors', [])):
                        row['State'] = 'Active'
                        msg = f'用户 {account} 已在组织中'
                        print(msg)
                        logging.info(msg)
                    elif response.get('failed_reason') is None:
                        row['State'] = 'Invited'
                        msg = f'向 {account} 发出邀请, 等待用户接受'
                        print(msg)
                        logging.info(msg)
                    else:
                        row['State'] = f'Error:please check log'
                        msg = f'邀请失败：{json.dumps(response)}'
                        print(f'错误: {msg}')
                        logging.error(msg)
                except Exception as e:
                    msg = f'邀请失败: {str(e)}'
                    print(f'错误: {msg}')
                    logging.error(msg)
                    row['State'] = f'Error:please check log'
                
        # Write updated states back to CSV
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            logging.error(f"Failed to write to CSV file: {str(e)}")
            print(f"错误: Failed to write to CSV file: {str(e)}")
            
    except Exception as e:
        logging.error(f"Error processing CSV: {str(e)}")
        print(f"错误: Error processing CSV: {str(e)}")

def get_team_id(organization_name, team_name):
    """
    Get team ID by organization name and team name.
    """
    url = f'https://api.github.com/orgs/{organization_name}/teams'
    headers = {'Authorization': f'token {token}'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        teams = response.json()
        if not isinstance(teams, list):
            logging.error(f"Unexpected API response: {teams}")
            return None
            
        for team in teams:
            if isinstance(team, dict) and team.get('name') == team_name:
                team_id = team.get('id')
                logging.info(f"找到团队 {team_name} 的ID: {team_id}")
                return team_id
                
        # 如果团队不存在，记录警告信息
        logging.warning(f"团队 '{team_name}' 在组织 '{organization_name}' 中不存在")
        return None
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting team ID: {str(e)}")
        return None


def invite_user_by_email_to_team(organization_name, team_name, email):
    """
    Invite a user to a team using their email address.
    """
    team_id = get_team_id(organization_name, team_name)
    if team_id is None:
        msg = f"团队 {team_name} 在组织 {organization_name} 中不存在，跳过邀请用户 {email}"
        print(f"警告: {msg}")
        logging.warning(msg)
        return {"message": "Team not found", "skipped": True}
        
    url = f'https://api.github.com/orgs/{organization_name}/invitations'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    data = {'email': email, 'role': 'direct_member', 'team_ids': [team_id]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response_json = response.json()
        
        # 添加 response 到日志
        
        
        if response.status_code >= 400:
            logging.error(f"API Response for inviting user {email} to team {team_name}: {response.status_code} - {response.text}")
        else :
            logging.info(f"API Response for inviting user {email} to team {team_name}: {response.status_code} - {response.text}")  
        
        return response_json
        
    except Exception as e:
        logging.error(f"Error inviting user by email: {str(e)}")
        return None


if __name__ == "__main__":
    # Get organization name and CSV file from command line arguments or use defaults
    
    org_name = "OrgName" # Replace with your organization name
    csv_file = "team_user.csv" # Replace with your CSV file name
    
    msg = f'开始批量邀请用户到团队 {org_name}'
    print(msg)
    logging.info(msg)
    
    batch_invite_users_to_teams(org_name, csv_file)
    
    msg = '批量邀请用户到团队完成'
    print(msg)
    logging.info(msg)

