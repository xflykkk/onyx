'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  Clock,
  Package,
  HardDrive,
  User,
  MessageSquare,
  CheckCircle,
  XCircle,
  RefreshCw,
  Search,
  FileText,
  ChevronDown,
  ChevronRight,
  Eye,
  BarChart3,
  Code,
  Copy,
  Download
} from 'lucide-react';
import { 
  getLatestStreamLog, 
  getStreamLogsStats,
  getStreamLogsList,
  getStreamLogByFilename,
  getStreamLogRawContent
} from '@/lib/api';
import { 
  StreamLogDetail, 
  StreamLogsStats, 
  StreamLogListItem,
  StreamLogPacket
} from '@/types';
import { cn } from '@/lib/utils';

type DesignVariant = 'glassmorphism' | 'neumorphic';

interface StreamLogsProps {
  variant?: DesignVariant;
}

export default function StreamLogs({ variant = 'glassmorphism' }: StreamLogsProps) {
  const [logDetail, setLogDetail] = useState<StreamLogDetail | null>(null);
  const [stats, setStats] = useState<StreamLogsStats | null>(null);
  const [logsList, setLogsList] = useState<StreamLogListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedPackets, setExpandedPackets] = useState<Set<number>>(new Set());
  const [selectedView, setSelectedView] = useState<'latest' | 'list'>('latest');
  const [selectedLogFile, setSelectedLogFile] = useState<string | null>(null);
  const [rawContent, setRawContent] = useState<string | null>(null);
  const [showRawContent, setShowRawContent] = useState(false);
  const [filterPacketType, setFilterPacketType] = useState<string>('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const [latestLog, statsData, listData] = await Promise.all([
        getLatestStreamLog().catch(() => null),
        getStreamLogsStats(),
        getStreamLogsList()
      ]);

      setLogDetail(latestLog);
      setStats(statsData);
      setLogsList(listData.log_files);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = () => {
    loadData();
  };

  const handleSelectLogFile = async (filename: string) => {
    if (selectedLogFile === filename) {
      // 如果点击的是当前选中的文件，则取消选择回到列表
      setSelectedLogFile(null);
      setShowRawContent(false);
      setRawContent(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      // 直接加载原始内容
      const rawData = await getStreamLogRawContent(filename);
      // 尝试格式化JSON以便更好阅读
      let formattedContent = rawData.raw_content;
      try {
        const jsonData = JSON.parse(rawData.raw_content);
        formattedContent = JSON.stringify(jsonData, null, 2);
      } catch {
        // 如果不能解析为JSON，就使用原始内容
        formattedContent = rawData.raw_content;
      }
      
      setRawContent(formattedContent);
      setSelectedLogFile(filename);
      setShowRawContent(true);
      setSelectedView('latest'); // 切换到详情视图
      setLogDetail(null); // 清除摘要数据
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载日志文件失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToList = () => {
    setSelectedLogFile(null);
    setSelectedView('list');
    setShowRawContent(false);
    setRawContent(null);
  };

  const handleToggleView = async (filename: string) => {
    if (showRawContent) {
      // 切换到摘要视图
      setIsLoading(true);
      setError(null);
      
      try {
        const logData = await getStreamLogByFilename(filename);
        setLogDetail(logData);
        setShowRawContent(false);
        setRawContent(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载摘要信息失败');
      } finally {
        setIsLoading(false);
      }
    } else {
      // 切换到原始内容
      setIsLoading(true);
      setError(null);
      
      try {
        const rawData = await getStreamLogRawContent(filename);
        // 尝试格式化JSON以便更好阅读
        let formattedContent = rawData.raw_content;
        try {
          const jsonData = JSON.parse(rawData.raw_content);
          formattedContent = JSON.stringify(jsonData, null, 2);
        } catch {
          // 如果不能解析为JSON，就使用原始内容
          formattedContent = rawData.raw_content;
        }
        setRawContent(formattedContent);
        setShowRawContent(true);
        setLogDetail(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载原始内容失败');
      } finally {
        setIsLoading(false);
      }
    }
  };

  const togglePacketExpansion = (packetId: number) => {
    const newExpanded = new Set(expandedPackets);
    if (newExpanded.has(packetId)) {
      newExpanded.delete(packetId);
    } else {
      newExpanded.add(packetId);
    }
    setExpandedPackets(newExpanded);
  };

  const getCardClass = () => {
    return cn(
      'p-6 rounded-xl border',
      variant === 'glassmorphism'
        ? 'glass-strong border-white/20'
        : 'neuro-raised bg-white border-gray-200'
    );
  };

  const getTextClass = () => {
    return cn(
      variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
    );
  };

  const getSecondaryTextClass = () => {
    return cn(
      'opacity-70',
      variant === 'glassmorphism' ? 'text-glass' : 'text-gray-600'
    );
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString('zh-CN');
    } catch {
      return timestamp;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getPacketTypeColor = (type: string) => {
    const colors = {
      answer_piece: 'text-green-500',
      sub_question: 'text-blue-500',
      sub_query: 'text-cyan-500',
      documents: 'text-purple-500',
      context_docs: 'text-indigo-500',
      thinking: 'text-yellow-500',
      error: 'text-red-500',
      message_detail: 'text-orange-500',
      other: 'text-gray-500',
    };
    return colors[type as keyof typeof colors] || colors.other;
  };

  const filteredPackets = logDetail?.packets.filter(packet => 
    filterPacketType === 'all' || packet.packet_type === filterPacketType
  ) || [];

  const uniquePacketTypes = Array.from(
    new Set(logDetail?.packets.map(p => p.packet_type) || [])
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        >
          <RefreshCw className="w-8 h-8 text-blue-500" />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={cn('text-2xl font-bold', getTextClass())}>
            流式日志分析
            {selectedLogFile && (
              <span className={cn('text-lg font-normal ml-2', getSecondaryTextClass())}>
                - {selectedLogFile}
              </span>
            )}
          </h1>
          <p className={cn('text-sm mt-1', getSecondaryTextClass())}>
            {selectedLogFile 
              ? (showRawContent ? '查看原始JSON文件内容' : '查看解析后的摘要信息')
              : '实时查看和分析 SSE 流式响应数据'
            }
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Action Buttons (when viewing a specific file) */}
          {selectedLogFile && (
            <div className="flex items-center space-x-2">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => handleToggleView(selectedLogFile)}
                className={cn(
                  'flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                  showRawContent
                    ? variant === 'glassmorphism'
                      ? 'glass-effect text-white'
                      : 'neuro-pressed bg-blue-500 text-white'
                    : variant === 'glassmorphism'
                      ? 'glass-light text-glass hover:glass-effect'
                      : 'neuro-flat text-gray-600 hover:neuro-raised'
                )}
              >
                {showRawContent ? (
                  <>
                    <BarChart3 className="w-4 h-4" />
                    <span>查看摘要信息</span>
                  </>
                ) : (
                  <>
                    <Code className="w-4 h-4" />
                    <span>查看原始内容</span>
                  </>
                )}
              </motion.button>
              
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleBackToList}
                className={cn(
                  'flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                  variant === 'glassmorphism'
                    ? 'glass-light text-glass hover:glass-effect'
                    : 'neuro-flat text-gray-600 hover:neuro-raised'
                )}
              >
                <FileText className="w-4 h-4" />
                <span>返回列表</span>
              </motion.button>
            </div>
          )}

          {/* View Toggle (only show when not viewing a specific file) */}
          {!selectedLogFile && (
            <div className={cn(
              'flex rounded-lg p-1 space-x-1',
              variant === 'glassmorphism' ? 'glass-light' : 'neuro-flat bg-gray-100'
            )}>
              {[
                { mode: 'latest' as const, icon: Activity, label: '最新日志' },
                { mode: 'list' as const, icon: FileText, label: '日志列表' },
              ].map(({ mode, icon: Icon, label }) => (
                <motion.button
                  key={mode}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setSelectedView(mode)}
                  className={cn(
                    'flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                    selectedView === mode
                      ? variant === 'glassmorphism'
                        ? 'glass-effect text-white'
                        : 'neuro-pressed bg-blue-500 text-white'
                      : variant === 'glassmorphism'
                        ? 'text-glass hover:glass-light'
                        : 'text-gray-600 hover:neuro-flat'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                </motion.button>
              ))}
            </div>
          )}

          {/* Refresh Button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleRefresh}
            className={cn(
              'p-2 rounded-lg transition-all',
              variant === 'glassmorphism'
                ? 'glass-light text-glass hover:glass-effect'
                : 'neuro-flat text-gray-600 hover:neuro-raised'
            )}
          >
            <RefreshCw className="w-5 h-5" />
          </motion.button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            'p-4 rounded-lg border flex items-center space-x-2',
            variant === 'glassmorphism'
              ? 'bg-red-500/20 border-red-400/40 text-red-200'
              : 'bg-red-50 border-red-200 text-red-800'
          )}
        >
          <XCircle className="w-5 h-5" />
          <span>{error}</span>
        </motion.div>
      )}

      <AnimatePresence mode="wait">
        {(selectedView === 'latest' || selectedLogFile) && (
          <motion.div
            key="latest"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            {/* Stats Cards (only show for latest, not for selected file) */}
            {stats && !selectedLogFile && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  className={getCardClass()}
                >
                  <div className="flex items-center space-x-3">
                    <FileText className="w-8 h-8 text-blue-500" />
                    <div>
                      <p className={cn('text-sm', getSecondaryTextClass())}>
                        总日志数
                      </p>
                      <p className={cn('text-2xl font-bold', getTextClass())}>
                        {stats.total_logs}
                      </p>
                    </div>
                  </div>
                </motion.div>

                <motion.div
                  whileHover={{ scale: 1.02 }}
                  className={getCardClass()}
                >
                  <div className="flex items-center space-x-3">
                    <CheckCircle className="w-8 h-8 text-green-500" />
                    <div>
                      <p className={cn('text-sm', getSecondaryTextClass())}>
                        完整日志
                      </p>
                      <p className={cn('text-2xl font-bold', getTextClass())}>
                        {stats.complete_logs}
                      </p>
                    </div>
                  </div>
                </motion.div>

                <motion.div
                  whileHover={{ scale: 1.02 }}
                  className={getCardClass()}
                >
                  <div className="flex items-center space-x-3">
                    <HardDrive className="w-8 h-8 text-purple-500" />
                    <div>
                      <p className={cn('text-sm', getSecondaryTextClass())}>
                        总大小
                      </p>
                      <p className={cn('text-2xl font-bold', getTextClass())}>
                        {formatFileSize(stats.total_size)}
                      </p>
                    </div>
                  </div>
                </motion.div>

                <motion.div
                  whileHover={{ scale: 1.02 }}
                  className={getCardClass()}
                >
                  <div className="flex items-center space-x-3">
                    <Clock className="w-8 h-8 text-orange-500" />
                    <div>
                      <p className={cn('text-sm', getSecondaryTextClass())}>
                        最新时间
                      </p>
                      <p className={cn('text-sm font-medium', getTextClass())}>
                        {stats.latest_log_time ? formatTimestamp(stats.latest_log_time) : '无'}
                      </p>
                    </div>
                  </div>
                </motion.div>
              </div>
            )}

            {/* Raw Content Display */}
            {showRawContent && rawContent && (
              <div className={getCardClass()}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className={cn('text-xl font-semibold', getTextClass())}>
                    原始文件内容
                  </h2>
                  <div className="flex items-center space-x-2">
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        navigator.clipboard.writeText(rawContent);
                        // 这里可以添加复制成功的提示
                      }}
                      className={cn(
                        'flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                        variant === 'glassmorphism'
                          ? 'glass-light text-glass hover:glass-effect'
                          : 'neuro-flat text-gray-600 hover:neuro-raised'
                      )}
                    >
                      <Copy className="w-4 h-4" />
                      <span>复制</span>
                    </motion.button>
                    
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        const blob = new Blob([rawContent], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = selectedLogFile || 'stream_log.json';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                      }}
                      className={cn(
                        'flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                        variant === 'glassmorphism'
                          ? 'glass-light text-glass hover:glass-effect'
                          : 'neuro-flat text-gray-600 hover:neuro-raised'
                      )}
                    >
                      <Download className="w-4 h-4" />
                      <span>下载</span>
                    </motion.button>
                  </div>
                </div>
                
                <div className={cn(
                  'relative rounded-lg border p-4 h-[70vh] overflow-auto',
                  variant === 'glassmorphism'
                    ? 'bg-black/20 border-white/20'
                    : 'bg-gray-100 border-gray-200'
                )}>
                  <pre className={cn(
                    'text-xs whitespace-pre-wrap font-mono leading-relaxed',
                    variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
                  )}>
                    {rawContent}
                  </pre>
                </div>
                
                <div className={cn(
                  'text-xs mt-2 px-3 py-2 rounded border',
                  variant === 'glassmorphism'
                    ? 'bg-blue-500/20 border-blue-400/40 text-blue-200'
                    : 'bg-blue-50 border-blue-200 text-blue-800'
                )}>
                  💡 提示: 内容已自动格式化为易读的JSON格式。可以使用复制或下载按钮保存内容。
                </div>
              </div>
            )}

            {/* Latest Log Detail */}
            {logDetail && !showRawContent && (
              <div className="space-y-6">
                {/* Summary */}
                <div className={getCardClass()}>
                  <h2 className={cn('text-xl font-semibold mb-4', getTextClass())}>
                    {selectedLogFile ? '日志摘要' : '最新日志摘要'}
                  </h2>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <User className="w-4 h-4" />
                        <span className={cn('text-sm', getSecondaryTextClass())}>
                          用户: {logDetail.summary.user_email || 'N/A'}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <MessageSquare className="w-4 h-4" />
                        <span className={cn('text-sm', getSecondaryTextClass())}>
                          消息: {logDetail.summary.message?.substring(0, 50) || 'N/A'}...
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Activity className="w-4 h-4" />
                        <span className={cn('text-sm', getSecondaryTextClass())}>
                          智能搜索: {logDetail.summary.use_agentic_search ? '是' : '否'}
                        </span>
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <Package className="w-4 h-4" />
                        <span className={cn('text-sm', getSecondaryTextClass())}>
                          数据包: {logDetail.summary.total_packets}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Search className="w-4 h-4" />
                        <span className={cn('text-sm', getSecondaryTextClass())}>
                          子问题: {logDetail.sub_questions.length}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <FileText className="w-4 h-4" />
                        <span className={cn('text-sm', getSecondaryTextClass())}>
                          文档数: {logDetail.documents_count}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Packet Types */}
                  <div className="mt-6">
                    <h3 className={cn('text-lg font-medium mb-3', getTextClass())}>
                      数据包类型统计
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(logDetail.summary.packet_types).map(([type, count]) => (
                        <div
                          key={type}
                          className={cn(
                            'px-3 py-1 rounded-full text-sm',
                            variant === 'glassmorphism'
                              ? 'glass-light'
                              : 'neuro-flat bg-gray-100'
                          )}
                        >
                          <span className={getPacketTypeColor(type)}>
                            {type}
                          </span>
                          <span className={cn('ml-2', getTextClass())}>
                            {count}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Sub Questions */}
                {logDetail.sub_questions.length > 0 && (
                  <div className={getCardClass()}>
                    <h2 className={cn('text-xl font-semibold mb-4', getTextClass())}>
                      子问题分析 ({logDetail.sub_questions.length} 个)
                    </h2>
                    <div className="space-y-3">
                      {logDetail.sub_questions.map((sq, index) => (
                        <div
                          key={index}
                          className={cn(
                            'p-3 rounded-lg border',
                            variant === 'glassmorphism'
                              ? 'glass-light border-white/20'
                              : 'neuro-flat border-gray-200'
                          )}
                        >
                          <div className="flex items-start space-x-3">
                            <span className={cn(
                              'px-2 py-1 rounded-md text-xs font-medium',
                              'bg-blue-500/20 text-blue-400'
                            )}>
                              [{sq.level}.{sq.num}]
                            </span>
                            <p className={cn('text-sm', getTextClass())}>
                              {sq.question}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Packets Detail */}
                <div className={getCardClass()}>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className={cn('text-xl font-semibold', getTextClass())}>
                      数据包详情 ({filteredPackets.length} 个)
                    </h2>
                    
                    {/* Packet Type Filter */}
                    <select
                      value={filterPacketType}
                      onChange={(e) => setFilterPacketType(e.target.value)}
                      className={cn(
                        'px-3 py-1 rounded-lg text-sm border',
                        variant === 'glassmorphism'
                          ? 'glass-light border-white/20 text-glass'
                          : 'neuro-flat border-gray-200 text-gray-800'
                      )}
                    >
                      <option value="all">所有类型</option>
                      {uniquePacketTypes.map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {filteredPackets.slice(0, 20).map((packet, index) => (
                      <motion.div
                        key={packet.sequence}
                        className={cn(
                          'border rounded-lg transition-all',
                          variant === 'glassmorphism'
                            ? 'glass-light border-white/20'
                            : 'neuro-flat border-gray-200'
                        )}
                      >
                        <button
                          onClick={() => togglePacketExpansion(packet.sequence)}
                          className="w-full p-3 text-left flex items-center justify-between"
                        >
                          <div className="flex items-center space-x-3">
                            <span className={cn(
                              'px-2 py-1 rounded-md text-xs font-medium',
                              'bg-gray-500/20 text-gray-400'
                            )}>
                              #{packet.sequence}
                            </span>
                            <span className={cn(
                              'px-2 py-1 rounded-md text-xs font-medium',
                              getPacketTypeColor(packet.packet_type)
                            )}>
                              {packet.packet_type}
                            </span>
                            <span className={cn('text-sm', getSecondaryTextClass())}>
                              {formatFileSize(packet.data_size)}
                            </span>
                          </div>
                          {expandedPackets.has(packet.sequence) ? 
                            <ChevronDown className="w-4 h-4" /> : 
                            <ChevronRight className="w-4 h-4" />
                          }
                        </button>
                        
                        <AnimatePresence>
                          {expandedPackets.has(packet.sequence) && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.2 }}
                              className="overflow-hidden"
                            >
                              <div className="p-3 pt-0 border-t border-white/10">
                                <div className="space-y-2 text-sm">
                                  <p className={getSecondaryTextClass()}>
                                    时间: {formatTimestamp(packet.timestamp)}
                                  </p>
                                  {packet.parsed_data.answer_piece && (
                                    <div>
                                      <span className={getSecondaryTextClass()}>答案片段: </span>
                                      <span className={getTextClass()}>
                                        {packet.parsed_data.answer_piece.substring(0, 200)}
                                        {packet.parsed_data.answer_piece.length > 200 ? '...' : ''}
                                      </span>
                                    </div>
                                  )}
                                  {packet.parsed_data.sub_question && (
                                    <div>
                                      <span className={getSecondaryTextClass()}>子问题: </span>
                                      <span className={getTextClass()}>
                                        {packet.parsed_data.sub_question}
                                      </span>
                                    </div>
                                  )}
                                  {packet.parsed_data.top_documents && (
                                    <div>
                                      <span className={getSecondaryTextClass()}>文档数量: </span>
                                      <span className={getTextClass()}>
                                        {packet.parsed_data.top_documents.length}
                                      </span>
                                    </div>
                                  )}
                                  <details className="mt-2">
                                    <summary className={cn(
                                      'cursor-pointer text-xs',
                                      getSecondaryTextClass()
                                    )}>
                                      查看原始数据
                                    </summary>
                                    <pre className={cn(
                                      'mt-2 p-2 rounded text-xs overflow-x-auto',
                                      variant === 'glassmorphism'
                                        ? 'bg-black/20 text-glass'
                                        : 'bg-gray-100 text-gray-800'
                                    )}>
                                      {JSON.stringify(packet.parsed_data, null, 2)}
                                    </pre>
                                  </details>
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.div>
                    ))}
                    
                    {filteredPackets.length > 20 && (
                      <div className={cn(
                        'text-center py-3 text-sm',
                        getSecondaryTextClass()
                      )}>
                        ... 还有 {filteredPackets.length - 20} 个数据包
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {!logDetail && !isLoading && (
              <div className={cn(
                'text-center py-12',
                getSecondaryTextClass()
              )}>
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>暂无流式日志数据</p>
              </div>
            )}
          </motion.div>
        )}

        {selectedView === 'list' && !selectedLogFile && (
          <motion.div
            key="list"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className={getCardClass()}
          >
            <h2 className={cn('text-xl font-semibold mb-4', getTextClass())}>
              历史日志列表
            </h2>
            
            {logsList.length > 0 ? (
              <div className="space-y-3">
                {logsList.map((log, index) => (
                  <motion.div
                    key={log.filename}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => handleSelectLogFile(log.filename)}
                    className={cn(
                      'p-4 rounded-lg border cursor-pointer transition-all',
                      variant === 'glassmorphism'
                        ? 'glass-light border-white/20 hover:glass-effect'
                        : 'neuro-flat border-gray-200 hover:neuro-raised'
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        <span className={cn('font-medium', getTextClass())}>
                          {log.filename}
                        </span>
                        {log.complete ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500" />
                        )}
                        <Eye className="w-4 h-4 opacity-50" />
                      </div>
                      <span className={cn('text-sm', getSecondaryTextClass())}>
                        {formatTimestamp(log.start_time)}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className={getSecondaryTextClass()}>用户: </span>
                        <span className={getTextClass()}>{log.user_email || 'N/A'}</span>
                      </div>
                      <div>
                        <span className={getSecondaryTextClass()}>数据包: </span>
                        <span className={getTextClass()}>{log.total_packets}</span>
                      </div>
                      <div>
                        <span className={getSecondaryTextClass()}>消息: </span>
                        <span className={getTextClass()}>{log.message_preview || 'N/A'}</span>
                      </div>
                    </div>
                    
                    <div className={cn(
                      'mt-3 pt-3 border-t border-opacity-20 text-xs flex items-center justify-center space-x-2',
                      variant === 'glassmorphism' ? 'border-white' : 'border-gray-300',
                      getSecondaryTextClass()
                    )}>
                      <Code className="w-3 h-3" />
                      <span>点击查看原始JSON内容（可切换到摘要）</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className={cn(
                'text-center py-8',
                getSecondaryTextClass()
              )}>
                <FileText className="w-8 h-8 mx-auto mb-3 opacity-50" />
                <p>暂无历史日志</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}