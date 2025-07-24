'use client';

import React, { ReactNode } from 'react';
import { createPortal } from 'react-dom';

/**
 * TooltipPortal - 将 tooltip 渲染到 document.body，确保不被遮挡
 */
interface TooltipPortalProps {
  children: ReactNode;
}

export const TooltipPortal: React.FC<TooltipPortalProps> = ({ children }) => {
  // 确保只在客户端渲染
  if (typeof window === 'undefined') {
    return null;
  }

  // 创建或获取 tooltip 容器
  let tooltipContainer = document.getElementById('tooltip-portal-root');
  if (!tooltipContainer) {
    tooltipContainer = document.createElement('div');
    tooltipContainer.id = 'tooltip-portal-root';
    tooltipContainer.style.position = 'absolute';
    tooltipContainer.style.top = '0';
    tooltipContainer.style.left = '0';
    tooltipContainer.style.zIndex = '999999';
    tooltipContainer.style.pointerEvents = 'none';
    document.body.appendChild(tooltipContainer);
  }

  return createPortal(children, tooltipContainer);
};