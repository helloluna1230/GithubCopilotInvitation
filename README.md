# GithubCopilotInvitation

## 项目简介
本项目用于管理 GitHub Copilot 团队用户的邀请和验证流程。

## 文件结构
- `invite_2_teams_verify.py`：主脚本，用于处理团队邀请和验证。
- `team_user.csv`：团队用户数据的 CSV 文件模板。
- `README.md`：项目说明文档。

## 注意事项
1. **环境变量设置**  
   管理员需要设置 `GITHUB_TOKEN` 环境变量，用于访问 GitHub API。

2. **脚本配置**  
   修改 `invite_2_teams_verify.py` 中的以下变量：
   ```python
   org_name = "OrgName"  # 替换为您的组织名称
   csv_file = "team_user.csv"  # 替换为您的 CSV 文件名称
   ```

3. **CSV 文件格式**  
   - 文件需以逗号分隔，至少包含以下列名：  
     `Team`, `Account`, `State`  
   - 脚本会读取 `Team` 和 `Account` 列，将用户邀请到对应的 GitHub 团队中，并更新 `State` 列的状态。

   **State 状态说明**：
   - `Active`：用户已存在于组织中。
   - `Invited`：邀请已发送，等待用户接受。
   - `Error:API failure`：邀请失败，请手动添加。

4. **日志记录**  
   邀请过程中的日志会写入 `invite.log` 文件，便于排查问题。

## 执行方法
运行以下命令执行脚本：
```bash
python ./invite_2_teams_verify.py
```