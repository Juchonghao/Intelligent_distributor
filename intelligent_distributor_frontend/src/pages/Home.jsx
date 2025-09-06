// src/pages/Home.jsx (最終打磨版)

import React from 'react';
import { Link } from 'react-router-dom';
import Beams from '../components/Beams/Beams';
import { SiBilibili, SiXiaohongshu } from 'react-icons/si';
import { FaTiktok } from 'react-icons/fa';

function Home() {
  return (
    <div className="relative w-screen h-screen overflow-hidden bg-black text-white">
    <div className="absolute top-20 left-40 z-20 font-semibold text-xl text-white tracking-widest animate-fade-in-slide-up">
        THEPAI
      </div>
      {/* 背景層 */}
      <div className="absolute inset-0 z-0">
        <Beams
          beamWidth={3}
          beamHeight={20}
          beamNumber={10}
          lightColor="#ffffff"
          speed={1.5}
          noiseIntensity={1.5}
          scale={0.15}
          rotation={-15}
        />
      </div>

      {/* 內容層 */}
      <div className="absolute inset-0 z-10 flex items-center justify-center">

        {/* 使用 Flexbox 和 space-y 來創造一個更大、更一致的垂直間距 */}
        <div className="flex flex-col items-center space-y-12 md:space-y-16">

          {/* 內容區塊 1: 標題和副標題 */}
          <div className="text-center animate-fade-in-slide-up delay-100">
            <div className="mb-4 px-4 py-1.5 backdrop-blur rounded-full text-xl">
              智能视频分发代理
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight max-w-4xl">
              AI-Powered Video Agent
            </h1>
            {/* ✨ 修改點 2: 提亮副標題顏色並增加陰影 */}
            <p className="mt-6 text-lg text-gray-400 max-w-2xl mx-auto drop-shadow-lg">
              AI 智能分析，一键分发至各大主流平台
            </p>
          </div>

          {/* 內容區塊 2: 按鈕 */}
          <div className="animate-fade-in-slide-up delay-200">
            <Link
              to="/agent"
              className="px-8 py-4 bg-white text-black font-semibold rounded-lg shadow-lg hover:bg-gray-200 transition-all duration-300 transform hover:scale-105"
            >
              开始使用
            </Link>
          </div>

          {/* 內容區塊 3: 平台圖示 */}
          <div className="flex flex-col items-center animate-fade-in-slide-up delay-300">
            {/* ✨ 修改點 2: 提亮文字顏色並增加陰影 */}
            <p className="text-xs text-gray-500 tracking-widest uppercase drop-shadow-md">
              支持平台
            </p>
            {/* ✨ 修改點 2: 提亮圖示顏色 */}
            <div className="flex items-center space-x-8 mt-4 text-2xl text-gray-500">
              <SiBilibili className="hover:text-white transition-colors"/>
              <SiXiaohongshu className="hover:text-white transition-colors"/>
              <FaTiktok className="hover:text-white transition-colors"/>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default Home;