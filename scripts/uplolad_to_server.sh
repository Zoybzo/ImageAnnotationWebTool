#!/usr/bin/env bash
# 用法: ./upload.sh <本地文件夹路径> <远程目标路径>
# 示例: ./upload.sh ./data /home/lingrun.1/

set -euo pipefail

# if [ $# -lt 2 ]; then
#   echo "用法: $0 <本地文件夹路径> <远程目标路径>"
#   exit 1
# fi

LOCAL_DIR="../ImageAnnotations"
REMOTE_DIR="/home/lingrun.1/Projects/ImageAnnotations"
SERVER="jd-ws"   # 就是 ~/.ssh/config 里定义的 Host

echo ">>> 上传 $LOCAL_DIR 到 $SERVER:$REMOTE_DIR ..."
rsync -avz --progress --files-from=<(git ls-files) -e "ssh" "$LOCAL_DIR" "$SERVER:$REMOTE_DIR"