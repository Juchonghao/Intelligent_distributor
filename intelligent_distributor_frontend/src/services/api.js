// src/services/api.js
const API_BASE_URL = 'http://127.0.0.1:8001/api';

export async function analyzeVideo(videoFile) {
  const formData = new FormData();
  formData.append('video', videoFile);
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error('视频分析失败');
  }
  return response.json();
}

export async function uploadToPlatform(data) {
  // ... 封装上传逻辑
}

export async function loginToPlatform(platform) {
  // ... 封装登录逻辑
}