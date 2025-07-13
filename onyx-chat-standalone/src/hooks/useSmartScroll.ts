import { RefObject, MutableRefObject, useEffect, useRef } from 'react';

export interface UseSmartScrollProps {
  chatState: 'idle' | 'sending' | 'streaming';
  scrollableDivRef: RefObject<HTMLDivElement>;
  endDivRef: RefObject<HTMLDivElement>;
  enableAutoScroll?: boolean;
  mobile?: boolean;
}

/**
 * 智能滚动管理 Hook
 * 借鉴 onyx/web 的 useScrollonStream 实现
 * 处理流式输出时的自动滚动，同时避免干扰用户主动滚动
 */
export function useSmartScroll({
  chatState,
  scrollableDivRef,
  endDivRef,
  enableAutoScroll = true,
  mobile = false,
}: UseSmartScrollProps) {
  const mobileDistance = 900; // 移动端滚动触发距离
  const desktopDistance = 500; // 桌面端滚动触发距离
  
  const distance = mobile ? mobileDistance : desktopDistance;
  
  // 防止滚动干扰的标志
  const preventScrollInterference = useRef<boolean>(false);
  const preventScroll = useRef<boolean>(false);
  const blockActionRef = useRef<boolean>(false);
  const previousScroll = useRef<number>(0);
  const scrollDist = useRef<number>(0);
  
  // 用户滚动检测
  const userHasScrolled = useRef<boolean>(false);
  const lastAutoScrollTime = useRef<number>(0);
  
  // 计算距离底部的距离
  const updateScrollDistance = () => {
    if (!scrollableDivRef.current) return;
    
    const element = scrollableDivRef.current;
    const scrollTop = element.scrollTop;
    const scrollHeight = element.scrollHeight;
    const clientHeight = element.clientHeight;
    
    scrollDist.current = scrollHeight - scrollTop - clientHeight;
  };
  
  // 检测用户是否主动滚动
  const detectUserScroll = () => {
    if (!scrollableDivRef.current) return;
    
    const now = Date.now();
    const timeSinceLastAutoScroll = now - lastAutoScrollTime.current;
    
    // 如果距离上次自动滚动超过 500ms，认为是用户主动滚动
    if (timeSinceLastAutoScroll > 500) {
      const newScrollTop = scrollableDivRef.current.scrollTop;
      const heightDifference = newScrollTop - previousScroll.current;
      
      // 用户向上滚动
      if (heightDifference < 0) {
        userHasScrolled.current = true;
        console.log('🎯 User scrolled up, auto-scroll disabled');
      }
      // 用户滚动到底部附近，重新启用自动滚动
      else if (scrollDist.current < 100) {
        userHasScrolled.current = false;
        console.log('🎯 User scrolled to bottom, auto-scroll enabled');
      }
    }
    
    previousScroll.current = scrollableDivRef.current.scrollTop;
  };
  
  // 执行智能滚动
  const performSmartScroll = () => {
    if (!enableAutoScroll || !scrollableDivRef.current || !endDivRef.current) {
      return;
    }
    
    // 如果用户主动滚动过，不自动滚动
    if (userHasScrolled.current) {
      return;
    }
    
    updateScrollDistance();
    
    // 如果接近底部，执行自动滚动
    if (scrollDist.current < distance && !blockActionRef.current && !preventScroll.current) {
      lastAutoScrollTime.current = Date.now();
      
      // 如果距离底部较远，直接跳转到底部
      if (scrollDist.current > 300) {
        endDivRef.current.scrollIntoView({ behavior: 'smooth' });
        console.log('🚀 Auto-scroll: Jump to bottom');
      } else {
        // 否则平滑滚动
        blockActionRef.current = true;
        
        const scrollAmount = scrollDist.current + (mobile ? 1000 : 10000);
        scrollableDivRef.current.scrollBy({
          left: 0,
          top: Math.max(0, scrollAmount),
          behavior: 'smooth',
        });
        
        console.log('🚀 Auto-scroll: Smooth scroll', scrollAmount);
        
        setTimeout(() => {
          blockActionRef.current = false;
        }, mobile ? 1000 : 500);
      }
    }
  };
  
  // 监听滚动事件
  useEffect(() => {
    const scrollElement = scrollableDivRef.current;
    if (!scrollElement) return;
    
    const handleScroll = () => {
      updateScrollDistance();
      detectUserScroll();
    };
    
    scrollElement.addEventListener('scroll', handleScroll, { passive: true });
    
    return () => {
      scrollElement.removeEventListener('scroll', handleScroll);
    };
  }, []);
  
  // 主要滚动逻辑
  useEffect(() => {
    if (!enableAutoScroll) {
      return;
    }
    
    // 只在流式输出时执行自动滚动
    if (chatState === 'streaming') {
      updateScrollDistance();
      
      const newHeight = scrollableDivRef.current?.scrollTop || 0;
      const heightDifference = newHeight - previousScroll.current;
      previousScroll.current = newHeight;
      
      // 防止滚动干扰逻辑
      if (heightDifference < 0 && !preventScroll.current) {
        if (scrollableDivRef.current) {
          scrollableDivRef.current.style.scrollBehavior = 'auto';
          scrollableDivRef.current.scrollTop = scrollableDivRef.current.scrollTop;
          scrollableDivRef.current.style.scrollBehavior = 'smooth';
        }
        
        preventScrollInterference.current = true;
        preventScroll.current = true;
        
        setTimeout(() => {
          preventScrollInterference.current = false;
        }, 2000);
        
        setTimeout(() => {
          preventScroll.current = false;
        }, 10000);
      }
      // 恢复滚动
      else if (!preventScrollInterference.current) {
        preventScroll.current = false;
      }
      
      // 执行智能滚动
      performSmartScroll();
    }
  }, [chatState, enableAutoScroll, mobile]);
  
  // 公开方法：手动滚动到底部
  const scrollToBottom = (force = false) => {
    if (!endDivRef.current) return;
    
    if (force) {
      userHasScrolled.current = false;
    }
    
    lastAutoScrollTime.current = Date.now();
    endDivRef.current.scrollIntoView({ behavior: 'smooth' });
    console.log('🚀 Manual scroll to bottom');
  };
  
  // 公开方法：重置用户滚动状态
  const resetUserScrollState = () => {
    userHasScrolled.current = false;
    console.log('🔄 Reset user scroll state');
  };
  
  return {
    scrollToBottom,
    resetUserScrollState,
    userHasScrolled: userHasScrolled.current,
    scrollDistance: scrollDist.current,
  };
}