// 全局变量
let images = [];
let currentIndex = 0;
let annotations = {};

// DOM元素
const statusElement = document.getElementById('status');
const imageContainer = document.getElementById('imageContainer');
const controlsElement = document.getElementById('controls');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const folderPathInput = document.getElementById('folderPath');

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 添加键盘事件监听器
    document.addEventListener('keydown', handleKeyPress);
    
    // 尝试从localStorage恢复上次的文件夹路径
    const savedPath = localStorage.getItem('lastFolderPath');
    if (savedPath) {
        folderPathInput.value = savedPath;
    }
});

// 键盘事件处理
function handleKeyPress(event) {
    if (images.length === 0) return;
    
    switch(event.key.toLowerCase()) {
        case 'j':
            event.preventDefault();
            nextImage();
            break;
        case 'k':
            event.preventDefault();
            previousImage();
            break;
        case 'h':
            event.preventDefault();
            markBad();
            break;
        case 'l':
            event.preventDefault();
            markGood();
            break;
    }
}

// 加载图片
async function loadImages() {
    const folderPath = folderPathInput.value.trim();
    
    if (!folderPath) {
        showStatus('请输入文件夹路径', 'warning');
        return;
    }
    
    // 保存路径到localStorage
    localStorage.setItem('lastFolderPath', folderPath);
    
    showStatus('正在加载图片...', 'info');
    
    try {
        const response = await fetch('/api/images', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ folder_path: folderPath })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            images = data.images;
            currentIndex = 0;
            annotations = {};
            
            if (images.length > 0) {
                showStatus(`成功加载 ${images.length} 张图片`, 'success');
                showControls();
                updateProgress();
                displayCurrentImage();
            } else {
                showStatus('指定文件夹中没有找到图片文件', 'warning');
                hideControls();
            }
        } else {
            showStatus(`加载失败: ${data.error}`, 'warning');
        }
    } catch (error) {
        showStatus(`加载失败: ${error.message}`, 'warning');
        console.error('Error loading images:', error);
    }
}

// 显示当前图片
function displayCurrentImage() {
    if (images.length === 0) return;
    
    const imagePath = images[currentIndex];
    const imageName = imagePath.split(/[/\\]/).pop(); // 支持正斜杠和反斜杠
    
    // 正确处理路径编码，确保反斜杠被正确编码
    const encodedPath = encodeURIComponent(imagePath);
    
    imageContainer.innerHTML = `
        <img src="/api/image/?path=${encodedPath}" alt="${imageName}" 
             onload="imageLoaded()" onerror="imageError()">
`;
    
    updateStatus();
}

// 图片加载成功
function imageLoaded() {
    // 可以在这里添加图片加载成功的逻辑
}

// 图片加载失败
function imageError() {
    const imagePath = images[currentIndex];
    console.error(`图片加载失败: ${imagePath}`);
    
    imageContainer.innerHTML = `
        <div style="color: red; padding: 20px;">
            <h3>图片加载失败</h3>
            <p>路径: ${imagePath}</p>
            <p>请检查文件是否存在且可访问</p>
            <button onclick="retryLoadImage()" style="margin-top: 10px; padding: 5px 10px;">重试</button>
        </div>
    `;
}

// 重试加载图片
function retryLoadImage() {
    displayCurrentImage();
}

// 去重CSV文件
async function deduplicateCSV() {
    const statusElement = document.getElementById('deduplicateStatus');
    
    try {
        // 显示处理状态
        statusElement.style.display = 'block';
        statusElement.className = 'status info';
        statusElement.textContent = '正在生成去重CSV文件...';
        
        const response = await fetch('/api/deduplicate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            statusElement.className = 'status success';
            statusElement.innerHTML = `
                <h4>✅ 去重完成！</h4>
                <p>输出文件: ${data.output_file}</p>
                <p>原始记录数: ${data.original_count}</p>
                <p>去重后记录数: ${data.deduplicated_count}</p>
                <p>删除重复记录数: ${data.removed_count}</p>
                <p>质量分布: ${data.quality_distribution}</p>
            `;
        } else {
            statusElement.className = 'status warning';
            statusElement.textContent = `去重失败: ${data.error}`;
        }
    } catch (error) {
        statusElement.className = 'status warning';
        statusElement.textContent = `去重失败: ${error.message}`;
        console.error('去重错误:', error);
    }
}

// 上一张图片
function previousImage() {
    if (currentIndex > 0) {
        currentIndex--;
        displayCurrentImage();
        updateProgress();
    }
}

// 下一张图片
function nextImage() {
    if (currentIndex < images.length - 1) {
        currentIndex++;
        displayCurrentImage();
        updateProgress();
    }
}

// 标记为质量好
async function markGood() {
    await markImage('Good');
}

// 标记为质量差
async function markBad() {
    await markImage('Bad');
}

// 标记图片
async function markImage(quality) {
    if (images.length === 0) return;
    
    const imagePath = images[currentIndex];
    const imageName = imagePath.split('/').pop();
    
    // 保存标注
    annotations[imagePath] = {
        quality: quality,
        timestamp: new Date().toISOString()
    };
    
    // 显示状态
    showStatus(`已标记 "${imageName}" 为 ${quality}`, 'success');
    
    // 自动保存到CSV
    await saveAnnotations();
    
    // 自动跳转到下一张图片
    setTimeout(() => {
        if (currentIndex < images.length - 1) {
            nextImage();
        }
    }, 500);
}

// 保存标注到CSV
async function saveAnnotations() {
    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ annotations: annotations })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            console.error('保存失败:', data.error);
        }
    } catch (error) {
        console.error('保存标注时出错:', error);
    }
}

// 更新进度条
function updateProgress() {
    if (images.length === 0) return;
    
    const progress = ((currentIndex + 1) / images.length) * 100;
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `${currentIndex + 1} / ${images.length}`;
}

// 更新状态显示
function updateStatus() {
    if (images.length === 0) return;
    
    const imagePath = images[currentIndex];
    const imageName = imagePath.split('/').pop();
    const annotation = annotations[imagePath];
    
    let statusText = `当前图片: ${imageName}`;
    if (annotation) {
        statusText += ` (已标记为: ${annotation.quality})`;
    }
    
    showStatus(statusText, 'info');
}

// 显示状态
function showStatus(message, type = 'info') {
    statusElement.textContent = message;
    statusElement.className = `status ${type}`;
}

// 显示控制按钮
function showControls() {
    controlsElement.style.display = 'flex';
    progressContainer.style.display = 'block';
}

// 隐藏控制按钮
function hideControls() {
    controlsElement.style.display = 'none';
    progressContainer.style.display = 'none';
}
