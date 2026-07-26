import os
import re

directories = [
    "../frontend/app",
    "../frontend/components",
]

for directory in directories:
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith((".tsx", ".ts", ".js", ".jsx")):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()

                # Basic find and replace for classNames to make sure inline classes are there
                content = re.sub(r'className="app-container"', 'className="flex flex-col min-h-screen"', content)
                content = re.sub(r'className="main"', 'className="flex-1 p-8 max-w-7xl mx-auto w-full"', content)
                content = re.sub(r'className="page-header"', 'className="mb-8"', content)
                content = re.sub(r'className="sub"', 'className="text-gray-400 text-base mt-2"', content)
                content = re.sub(r'className="cards-row"', 'className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"', content)
                content = re.sub(r'className="stat-card"', 'className="bg-vssid p-6 rounded-lg border border-vshl shadow-sm flex flex-col justify-between hover:border-vsblue transition-colors"', content)
                content = re.sub(r'className="num"', 'className="text-4xl font-bold text-vsblue mb-2"', content)
                content = re.sub(r'className="lbl"', 'className="text-gray-400 text-sm font-medium"', content)
                content = re.sub(r'className="panel"', 'className="bg-vssid border border-vshl rounded-lg p-6 mb-8 shadow-sm"', content)
                content = re.sub(r'className="section-label"', 'className="font-semibold text-lg mb-5 pb-3 border-b border-vshl text-white flex items-center gap-2"', content)
                content = re.sub(r'className="wire"', 'className="w-full border-collapse text-left"', content)
                content = re.sub(r'className="btn"', 'className="px-4 py-2 bg-vshl border border-vshl rounded text-vstext font-medium cursor-pointer transition-colors hover:bg-gray-600 disabled:opacity-50 inline-flex items-center justify-center gap-2"', content)
                content = re.sub(r'className="btn primary"', 'className="px-4 py-2 bg-vsblue text-white rounded border border-vsblue font-medium cursor-pointer hover:bg-blue-600 disabled:opacity-50 inline-flex items-center justify-center gap-2"', content)
                content = re.sub(r'className="btn danger"', 'className="px-4 py-2 bg-transparent text-red-400 rounded border border-red-500/30 hover:bg-red-500/10 hover:border-red-500 font-medium cursor-pointer disabled:opacity-50 inline-flex items-center justify-center gap-2"', content)
                content = re.sub(r'className="empty"', 'className="p-10 text-center text-gray-500 italic"', content)
                content = re.sub(r'className="error-box"', 'className="bg-red-900/30 text-red-400 p-4 rounded border border-red-800 mb-5"', content)
                content = re.sub(r'className="info-box"', 'className="bg-vsblue/10 text-vsblue p-4 rounded border border-vsblue/30 mb-5"', content)
                content = re.sub(r'className="form-input"', 'className="w-full p-2.5 rounded bg-[#1e1e1e] border border-vshl text-vstext focus:border-vsblue focus:outline-none transition-colors"', content)
                content = re.sub(r'className="field"', 'className="w-full p-2.5 rounded bg-[#1e1e1e] border border-vshl text-vstext focus:border-vsblue focus:outline-none transition-colors"', content)
                content = re.sub(r'className="flabel"', 'className="block mb-2 font-medium text-sm text-gray-300"', content)
                content = re.sub(r'className="two-col"', 'className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start"', content)
                content = re.sub(r'className="activity-item"', 'className="py-3 border-b border-vshl flex justify-between items-center text-sm"', content)
                content = re.sub(r'className="time"', 'className="text-gray-500 text-xs ml-3"', content)
                
                with open(path, "w") as f:
                    f.write(content)
