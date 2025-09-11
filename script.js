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
const csvPathInput = document.getElementById('csvPath');
const csvFiltersInput = document.getElementById('csvFilters');
const singleImagePathInput = document.getElementById('singleImagePath');

// 简单HTML转义，避免路径/文件名中的特殊字符影响渲染
function escapeHtml(text) {
    if (text == null) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 添加键盘事件监听器
    document.addEventListener('keydown', handleKeyPress);
    
    // 尝试从localStorage恢复上次的文件夹路径
    const savedPath = localStorage.getItem('lastFolderPath');
    if (savedPath) {
        folderPathInput.value = savedPath;
    }

    // 恢复上次CSV路径
    const savedCSV = localStorage.getItem('lastCSVPath');
    if (savedCSV && csvPathInput) {
        csvPathInput.value = savedCSV;
    }

    const savedFilters = localStorage.getItem('lastCSVFilters');
    if (savedFilters && csvFiltersInput) {
        csvFiltersInput.value = savedFilters;
    }

    const savedSingle = localStorage.getItem('lastSingleImagePath');
    if (savedSingle && singleImagePathInput) {
        singleImagePathInput.value = savedSingle;
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

// 根据输入路径显示单张图片
function showSingleImage() {
    const path = (singleImagePathInput ? singleImagePathInput.value : '').trim();
    if (!path) {
        showStatus('请输入单张图片路径', 'warning');
        return;
    }
    localStorage.setItem('lastSingleImagePath', path);

    images = [path];
    currentIndex = 0;
    annotations = {};

    showStatus('正在加载图片...', 'info');
    showControls();
    updateProgress();
    displayCurrentImage();
}

// 从CSV加载图片
async function loadImagesFromCSV() {
    const csvPath = (csvPathInput ? csvPathInput.value : '').trim();

    if (!csvPath) {
        showStatus('请输入CSV文件路径', 'warning');
        return;
    }

    // 保存CSV路径到localStorage
    localStorage.setItem('lastCSVPath', csvPath);

    showStatus('正在从CSV加载图片...', 'info');

    try {
        const response = await fetch('/api/images_from_csv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ csv_path: csvPath })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            images = data.images;
            currentIndex = 0;
            annotations = {};

            // 预载入quality（如果返回了）
            if (data.qualities && typeof data.qualities === 'object') {
                for (const [imgPath, q] of Object.entries(data.qualities)) {
                    annotations[imgPath] = {
                        quality: q,
                        timestamp: new Date().toISOString()
                    };
                }
            }

            if (images.length > 0) {
                const invalidInfo = (data.invalid && data.invalid > 0) ? `，忽略无效条目 ${data.invalid} 个` : '';
                showStatus(`成功从CSV加载 ${images.length} 张图片${invalidInfo}`,'success');
                showControls();
                updateProgress();
                displayCurrentImage();
            } else {
                showStatus('CSV中没有有效的图片路径', 'warning');
                hideControls();
            }
        } else {
            showStatus(`加载失败: ${data.error}`, 'warning');
        }
    } catch (error) {
        showStatus(`加载失败: ${error.message}`, 'warning');
        console.error('Error loading images from CSV:', error);
    }
}

// 解析筛选输入，如："quality=Good; cid1=123,456"
function parseFiltersInput(text) {
    const filters = {};
    if (!text) return filters;
    const parts = text.split(';');
    for (const part of parts) {
        const seg = part.trim();
        if (!seg) continue;
        const eqIdx = seg.indexOf('=');
        if (eqIdx <= 0) continue;
        const key = seg.slice(0, eqIdx).trim();
        const valueRaw = seg.slice(eqIdx + 1).trim();
        if (!key) continue;
        if (valueRaw.includes(',')) {
            filters[key] = valueRaw.split(',').map(s => s.trim()).filter(Boolean);
        } else {
            filters[key] = valueRaw;
        }
    }
    return filters;
}

async function loadImagesFromCSVWithFilters() {
    const csvPath = (csvPathInput ? csvPathInput.value : '').trim();
    const filtersText = (csvFiltersInput ? csvFiltersInput.value : '').trim();

    if (!csvPath) {
        showStatus('请输入CSV文件路径', 'warning');
        return;
    }

    const filters = parseFiltersInput(filtersText);
    localStorage.setItem('lastCSVPath', csvPath);
    localStorage.setItem('lastCSVFilters', filtersText);

    showStatus('正在按筛选从CSV加载图片...', 'info');

    try {
        const response = await fetch('/api/images_from_csv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ csv_path: csvPath, filters })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            images = data.images;
            currentIndex = 0;
            annotations = {};

            if (data.qualities && typeof data.qualities === 'object') {
                for (const [imgPath, q] of Object.entries(data.qualities)) {
                    annotations[imgPath] = {
                        quality: q,
                        timestamp: new Date().toISOString()
                    };
                }
            }

            if (images.length > 0) {
                const invalidInfo = (data.invalid && data.invalid > 0) ? `，忽略无效条目 ${data.invalid} 个` : '';
                showStatus(`成功从CSV加载 ${images.length} 张图片${invalidInfo}`,'success');
                showControls();
                updateProgress();
                displayCurrentImage();
            } else {
                showStatus('筛选后没有有效的图片路径', 'warning');
                hideControls();
            }
        } else {
            showStatus(`加载失败: ${data.error}`, 'warning');
        }
    } catch (error) {
        showStatus(`加载失败: ${error.message}`, 'warning');
        console.error('Error loading images with filters:', error);
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
        <div style="display:flex; flex-direction:column; align-items:center; width:100%">
            <img src="/api/image/?path=${encodedPath}" alt="${escapeHtml(imageName)}" 
                 onload="imageLoaded()" onerror="imageError()">
            <div style="margin-top:10px; color:#555; font-size:14px; width:100%; max-width:1000px;">
                <div><strong>文件名</strong>: <span style="font-family:monospace">${escapeHtml(imageName)}</span></div>
                <div style="word-break:break-all"><strong>路径</strong>: <span style="font-family:monospace">${escapeHtml(imagePath)}</span></div>
            </div>
        </div>
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
