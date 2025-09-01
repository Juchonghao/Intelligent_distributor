<!--
SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Documentation Examples

This directory contains the code for examples used in documentation guides which are located under the `docs/source` directory.

## Installation and Setup

If you have not already done so, follow the instructions in the [Install Guide](../../docs/source/quick-start/installing.md#install-from-source) to create the development environment and install NeMo Agent Toolkit.

### Using Documentation Examples:

The examples in this directory are referenced in various documentation guides. Each subdirectory contains specific examples used in tutorials and guides. Refer to the main documentation for detailed instructions on running these examples.

好的，完全理解！我们不重复所有细节，只把最终成功跑通的**核心步骤**提炼出来，方便其他人（以及未来的您）快速上手。

您可以将下面的Markdown内容，添加到您现有的`README.md`文件中。

-----

## 🚀 如何运行 (How to Run)

本项目基于NVIDIA NeMo Agent Toolkit (NAT) 构建，请确保您已完成NAT的基础环境设置。

#### 1\. 环境准备 (Environment Setup)

在启动前，请确保您已安装本项目所需的核心依赖。在您的虚拟环境 (`.venv`) 中运行：

```bash
uv pip install dashscope
```

#### 2\. 配置 API Key

本项目使用阿里通义千问（qwen-vl-max）作为多模态分析模型。请前往[阿里通义千问官网](https://dashscope.console.aliyun.com/apiKey)获取您的API Key，并通过环境变量进行配置：

```bash
export DASHSCOPE_API_KEY='sk-xxxxxxxxxxxxxxxxxxxx'
```

> **提示**: 请将 `sk-xxx...` 替换为您自己的真实API Key。

#### 3\. 安装并注册自定义工具

为了让 `nat` 框架能够识别我们自定义的 `video_analyzer` 工具，需要运行以下命令来安装/注册我们的工作流。此命令会读取 `pyproject.toml` 中的入口点配置。

请在 `NeMo-Agent-Toolkit` 的根目录下运行：

```bash
nat workflow reinstall intelligent_distributor
```

看到 `Workflow 'intelligent_distributor' reinstalled successfully.` 即表示成功。

#### 4\. 运行代理！

一切就绪！现在您可以通过以下命令来启动AI代理。

请**将命令中的路径替换为您自己视频的绝对路径**。

```bash
nat run --config_file intelligent_distributor/src/intelligent_distributor/configs/config.yml --input "請分析这个影片 '[请替换为您的视频绝对路径]'，並告訴我它適合發布到哪些平台。"
```

代理启动后，将会调用通义千问模型对您的视频进行分析，并在终端返回JSON格式的发布平台建议。

-----
