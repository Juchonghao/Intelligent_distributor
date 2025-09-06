import React, { useState, useCallback, useRef, useEffect } from 'react';
import Beams from '../components/Beams/Beams';
import { Link } from 'react-router-dom';

// --- 静态资源与常量 ---
const platformIcons = {
  "B站": "https://www.bilibili.com/favicon.ico",
  "小红书": "https://www.xiaohongshu.com/favicon.ico",
  "抖音": "https://www.douyin.com/favicon.ico",
};
const API_BASE_URL = 'http://127.0.0.1:8000/api'; // 确保这里的端口和后端一致

// --- 图标组件 ---
const UploadIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
);
const Spinner = ({ className = "h-5 w-5" }) => (
    <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
    </svg>
);


// --- 主应用组件 ---
function App() {
  // --- 状态管理 (State) ---
  const [view, setView] = useState('upload');
  const [loginStatuses, setLoginStatuses] = useState({
    'B站': { status: 'idle', message: '' },
    '小红书': { status: 'idle', message: '' },
  });
  const [currentFile, setCurrentFile] = useState(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState('');
  const [uploadStatuses, setUploadStatuses] = useState({});

  // [新增] 封面生成相关状态
  const [isGeneratingThumbnail, setIsGeneratingThumbnail] = useState(false);
  const [thumbnailError, setThumbnailError] = useState('');


  const uploadInputRef = useRef(null);

  // --- 效果钩子 (Effect) ---
  useEffect(() => {
    if (currentFile) {
      const url = URL.createObjectURL(currentFile);
      setVideoPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [currentFile]);

  // --- 事件处理函数 ---
  const handleLogin = useCallback(async (platform) => {
    setLoginStatuses(prev => ({ ...prev, [platform]: { status: 'loading', message: '请求中...' } }));
    const formData = new FormData();
    formData.append('platform', platform);
    try {
      const response = await fetch(`${API_BASE_URL}/login`, { method: 'POST', body: formData });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '登入请求失败');
      setLoginStatuses(prev => ({ ...prev, [platform]: { status: 'prompt_scan', message: '登录成功' } }));
    } catch (error) {
      console.error(`登入 ${platform} 失败:`, error);
      setLoginStatuses(prev => ({ ...prev, [platform]: { status: 'error', message: `登入失败: ${error.message}` } }));
    }
  }, []);

  const handleFileAnalysis = useCallback(async (file) => {
    if (!file) return;
    setCurrentFile(file);
    setView('results');
    setIsAnalyzing(true);
    setAnalysisError('');
    setAnalysisResult(null);
    const formData = new FormData();
    formData.append('video', file);
    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, { method: 'POST', body: formData });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      setAnalysisResult(data);
    } catch (error) {
      console.error('分析请求失败:', error);
      setAnalysisError('分析失败，请检查后端服务是否已启动，或查看控制台日志。');
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const handleGenerateThumbnail = useCallback(async () => {
    if (!currentFile || !analysisResult) {
      setThumbnailError("缺少视频文件或分析结果，无法生成封面。");
      return;
    }
    setIsGeneratingThumbnail(true);
    setThumbnailError('');

    const formData = new FormData();
    formData.append('video', currentFile);
    // 注意：时间戳目前硬编码为第1秒，未来可以添加UI让用户选择
    formData.append('timestamp', '00:00:01.000');
    formData.append('title', analysisResult.title);
    formData.append('language', 'zh');

    try {
      const response = await fetch(`${API_BASE_URL}/generate_thumbnail`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      // 接收后端返回的视频文件流
      const blob = await response.blob();
      const newFileName = `video_with_thumbnail_${Date.now()}.mp4`;
      const newFile = new File([blob], newFileName, { type: 'video/mp4' });

      // 更新当前文件为带有封面的新视频，预览会自动更新
      setCurrentFile(newFile);

    } catch (error) {
      console.error('生成封面失败:', error);
      setThumbnailError(`生成封面失败: ${error.message}`);
    } finally {
      setIsGeneratingThumbnail(false);
    }
  }, [currentFile, analysisResult]);


  const handleUploadToPlatform = useCallback(async (platform) => {
    if (!currentFile || !analysisResult) {
      setUploadStatuses(prev => ({ ...prev, [platform]: { status: 'error', message: '缺少文件或分析数据' } }));
      return;
    }
    setUploadStatuses(prev => ({ ...prev, [platform]: { status: 'loading', message: '' } }));
    const formData = new FormData();
    formData.append('video', currentFile);
    formData.append('platform', platform);
    formData.append('title', analysisResult.title);
    formData.append('description', analysisResult.description);
    formData.append('tags_json', JSON.stringify(analysisResult.tags));
    try {
      const response = await fetch(`${API_BASE_URL}/upload`, { method: 'POST', body: formData });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '上传失败');
      setUploadStatuses(prev => ({ ...prev, [platform]: { status: 'success', message: '✓' } }));
    } catch (error) {
      console.error(`上传至 ${platform} 失败:`, error);
      setUploadStatuses(prev => ({ ...prev, [platform]: { status: 'error', message: `失败: ${error.message}` } }));
    }
  }, [currentFile, analysisResult]);

  const handleReset = () => {
    setView('upload');
    setCurrentFile(null);
    setVideoPreviewUrl('');
    setAnalysisResult(null);
    setAnalysisError('');
    setUploadStatuses({});
    setThumbnailError('');
    if(uploadInputRef.current) {
      uploadInputRef.current.value = '';
    }
  };

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.currentTarget.classList.add('border-indigo-500');
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('border-indigo-500');
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('border-indigo-500');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileAnalysis(e.dataTransfer.files[0]);
    }
  }, [handleFileAnalysis]);

  // --- 渲染 (Render) ---
  return (
      <div className="relative w-screen h-screen overflow-hidden bg-gray-900">
        <Link to="/" className="absolute top-20 left-40 z-20 font-semibold text-xl text-white tracking-widest animate-fade-in-slide-up">
          THEPAI
        </Link>
        <div className="absolute inset-0 z-0">
          <Beams beamWidth={2} beamHeight={15} beamNumber={12} lightColor="#ffffff" speed={2} noiseIntensity={1.75} scale={0.2} rotation={-15} />
        </div>
        <div className="relative z-10 flex items-center justify-center w-full h-full p-4 md:p-8">
          <div className="w-11/12 md:w-4/5 lg:w-3/4 h-auto md:h-5/6 flex flex-col bg-black/30 backdrop-blur-lg border border-white/10 shadow-2xl rounded-2xl overflow-hidden">
            <header className="p-8 border-b border-white/10 shrink-0 flex justify-between items-start">
              <div className="text-left">
                <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-br from-white to-gray-400">智能视频分发代理</h1>
                <p className="text-gray-400 mt-2">AI-Powered Video Distribution Agent</p>
              </div>
              <div className="flex items-start space-x-4">
                {Object.keys(loginStatuses).map(platform => (
                    <div key={platform} className="text-right">
                      <button
                          onClick={() => handleLogin(platform)}
                          disabled={loginStatuses[platform].status === 'loading' || loginStatuses[platform].status === 'prompt_scan'}
                          className={`font-bold py-2 px-4 rounded-lg border transition-all duration-300 transform hover:scale-105 ${loginStatuses[platform].status === 'prompt_scan' ? 'bg-green-600 border-green-600 text-white' : (platform === 'B站' ? 'bg-transparent border-sky-500 text-sky-400 hover:bg-sky-500/20' : 'bg-transparent border-red-500 text-red-500 hover:bg-red-500/20')}`}
                      >
                        {loginStatuses[platform].status === 'prompt_scan' ? `已请求${platform}` : `登入${platform}`}
                      </button>
                      <p className={`text-xs mt-1 h-4 ${loginStatuses[platform].status === 'loading' ? 'text-yellow-400' : loginStatuses[platform].status === 'prompt_scan' ? 'text-green-400' : loginStatuses[platform].status === 'error' ? 'text-red-400' : ''}`}>{loginStatuses[platform].message}</p>
                    </div>
                ))}
              </div>
            </header>

            <main className="p-8 overflow-y-auto grow space-y-6">
              {view === 'upload' && (
                  <div
                      className="border border-white/20 hover:border-sky-400 hover:bg-white/5 transition-all duration-300 rounded-xl p-12 text-center cursor-pointer"
                      onClick={() => uploadInputRef.current?.click()}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                  >
                    <div className="flex flex-col items-center pointer-events-none">
                      <UploadIcon />
                      <p className="mt-4 text-lg">拖拽视频文件到这里，或 <span className="font-semibold text-indigo-400">点击选择</span></p>
                      <p className="text-sm text-gray-500 mt-1">支持 MP4, MOV 等格式</p>
                      <input type="file" className="hidden" accept="video/*" ref={uploadInputRef} onChange={(e) => handleFileAnalysis(e.target.files[0])} />
                    </div>
                  </div>
              )}

              {view === 'results' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8 h-full">
                    <div className="space-y-4 flex flex-col">
                      <h2 className="text-xl font-semibold shrink-0 text-white drop-shadow-md">视频预览</h2>
                      <div className="w-full aspect-video rounded-lg bg-black overflow-hidden shrink-0">
                        <video className="w-full h-full object-contain" controls src={videoPreviewUrl}></video>
                      </div>
                      <div className="text-sm text-gray-400">{currentFile && `文件名: ${currentFile.name}`}</div>
                      {/* [新增] 显示封面生成错误信息 */}
                      {thumbnailError && <p className="text-sm text-red-400">{thumbnailError}</p>}
                      <div className="pt-2 flex justify-center items-center gap-x-4">
                        <button
                            className="bg-gray-700/50 hover:bg-gray-600/50 border border-gray-600 text-gray-300 font-bold py-3 px-8 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={handleReset}
                            disabled={isAnalyzing || isGeneratingThumbnail}
                        >
                          上传另一个视频
                        </button>
                        {/* [修改] 封面生成按钮 */}
                        <button
                            className="bg-indigo-600/50 hover:bg-indigo-500/50 border border-indigo-500 text-indigo-300 font-bold py-3 px-8 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                            onClick={handleGenerateThumbnail}
                            disabled={isAnalyzing || !analysisResult || isGeneratingThumbnail}
                        >
                          {isGeneratingThumbnail ? (
                              <><Spinner className="h-5 w-5 mr-2" /> 生成中...</>
                          ) : (
                              "一键生成封面"
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="space-y-4 flex flex-col">
                      <div className="flex justify-between items-center shrink-0">
                        <h2 className={`text-xl font-semibold ${analysisError ? 'text-red-400' : 'text-white drop-shadow-md'}`}>
                          {analysisError ? '分析失败' : 'AI 平台推荐'}
                        </h2>
                        {isAnalyzing && (<div className="flex items-center space-x-2 text-sm text-indigo-400"><Spinner /><span>分析中...</span></div>)}
                        {!isAnalyzing && !analysisError && analysisResult && (<span className="text-sm text-green-400">分析完成！</span>)}
                      </div>
                      {!isAnalyzing && !analysisError && analysisResult && (
                          <div className="bg-white/5 border border-white/10 p-4 rounded-xl space-y-2 animate-fade-in shrink-0">
                            <h3 className="font-semibold text-white">AI 生成内容</h3>
                            <div><label className="text-xs font-medium text-gray-400">标题</label><p className="text-sm text-gray-200">{typeof analysisResult.title === 'object' ? analysisResult.title.zh : analysisResult.title}</p></div>
                            <div><label className="text-xs font-medium text-gray-400">描述</label><p className="text-sm text-gray-200 whitespace-pre-wrap">{analysisResult.description}</p></div>
                            <div>
                              <label className="text-xs font-medium text-gray-400">标签</label>
                              <div className="flex flex-wrap gap-2 mt-1">
                                {Array.isArray(analysisResult.tags) && analysisResult.tags.map(tag => (<span key={tag} className="bg-gray-700 text-xs font-medium text-indigo-300 px-2.5 py-1 rounded-full">{tag}</span>))}
                              </div>
                            </div>
                          </div>
                      )}
                      <div className="space-y-3 overflow-y-auto grow">
                        {analysisError && <div className="bg-gray-700 p-4 rounded-lg text-red-300">{analysisError}</div>}
                        {!isAnalyzing && analysisResult?.recommendations?.map(rec => {
                          const uploadStatus = uploadStatuses[rec.platform] || { status: 'idle' };
                          const suitabilityStars = '⭐'.repeat(rec.suitability) + '☆'.repeat(5 - rec.suitability);
                          const getButtonContent = () => {
                            switch (uploadStatus.status) {
                              case 'loading': return <><Spinner className="h-4 w-4 inline-block mr-2" />上传中...</>;
                              case 'success': return '上传成功';
                              case 'error': return '重试上传';
                              default: return `上传至 ${rec.platform}`;
                            }
                          };
                          const getButtonClasses = () => {
                            switch (uploadStatus.status) {
                              case 'success': return 'bg-green-600 border-green-600 text-white';
                              case 'error': return 'bg-red-600 hover:bg-red-700 border-red-600 text-white';
                              default: return 'bg-gray-700/50 hover:bg-gray-600/50 border-gray-600 text-gray-300';
                            }
                          };
                          return (
                              <div key={rec.platform} className="bg-white/5 border border-white/10 p-4 rounded-xl animate-fade-in space-y-3">
                                <div className="flex items-start space-x-4">
                                  <img src={platformIcons[rec.platform]} className="h-6 w-6 rounded-sm mt-1" alt={rec.platform} />
                                  <div className="flex-1">
                                    <div className="flex justify-between items-center">
                                      <h3 className="font-bold text-white">{rec.platform}</h3>
                                      <div className="text-sm text-yellow-400">{suitabilityStars}</div>
                                    </div>
                                    <p className="text-xs text-gray-300 mt-1">{rec.reason}</p>
                                  </div>
                                </div>
                                <div className="text-right">
                                  <button
                                      className={`upload-btn text-xs font-semibold px-4 py-1.5 border rounded-md transition-colors ${getButtonClasses()}`}
                                      disabled={uploadStatus.status === 'loading' || uploadStatus.status === 'success'}
                                      onClick={() => handleUploadToPlatform(rec.platform)}
                                  >
                                    {getButtonContent()}
                                  </button>
                                  <span className={`upload-status text-xs ml-2 ${uploadStatus.status === 'success' ? 'text-green-400' : 'text-red-400'}`}>{uploadStatus.message}</span>
                                </div>
                              </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
              )}
            </main>
          </div>
        </div>
      </div>
  );
}

export default App;