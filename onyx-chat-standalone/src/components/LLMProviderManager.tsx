'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Edit,
  Trash2,
  TestTube,
  Star,
  Eye,
  Settings,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Save,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  LLMProvider,
  CreateLLMProviderRequest,
  TestLLMProviderRequest,
  ModelConfiguration,
} from '@/types';
import {
  getLLMProviders,
  createLLMProvider,
  updateLLMProvider,
  deleteLLMProvider,
  testLLMProvider,
  setDefaultProvider,
} from '@/lib/api';

type DesignVariant = 'glassmorphism' | 'neumorphic';

interface LLMProviderManagerProps {
  variant?: DesignVariant;
}

const PROVIDER_TYPES = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'azure', label: 'Azure OpenAI' },
  { value: 'bedrock', label: 'AWS Bedrock' },
  { value: 'vertex_ai', label: 'Google Vertex AI' },
];

const PROVIDER_DEFAULTS = {
  openai: {
    api_base: 'https://api.openai.com/v1',
    default_model_name: 'gpt-4o',
    fast_default_model_name: 'gpt-4o-mini',
    default_vision_model: 'gpt-4o',
    max_input_tokens: 128000,
    api_version: undefined as string | undefined,
    deployment_name: undefined as string | undefined,
  },
  anthropic: {
    api_base: 'https://api.anthropic.com',
    default_model_name: 'claude-3-5-sonnet-20241022',
    fast_default_model_name: 'claude-3-5-haiku-20241022',
    default_vision_model: 'claude-3-5-sonnet-20241022',
    max_input_tokens: 200000,
    api_version: undefined as string | undefined,
    deployment_name: undefined as string | undefined,
  },
  azure: {
    api_base: 'https://your-resource.openai.azure.com',
    default_model_name: 'gpt-4o',
    fast_default_model_name: 'gpt-4o-mini',
    default_vision_model: 'gpt-4o',
    api_version: '2024-02-01',
    deployment_name: 'gpt-4o',
    max_input_tokens: 128000,
  },
  bedrock: {
    api_base: 'https://bedrock-runtime.us-east-1.amazonaws.com',
    default_model_name: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
    fast_default_model_name: 'anthropic.claude-3-5-haiku-20241022-v1:0',
    default_vision_model: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
    max_input_tokens: 200000,
    api_version: undefined as string | undefined,
    deployment_name: undefined as string | undefined,
  },
  vertex_ai: {
    api_base: 'https://us-central1-aiplatform.googleapis.com/v1',
    default_model_name: 'gemini-1.5-pro',
    fast_default_model_name: 'gemini-1.5-flash',
    default_vision_model: 'gemini-1.5-pro',
    max_input_tokens: 1000000,
    api_version: undefined as string | undefined,
    deployment_name: undefined as string | undefined,
  },
} as const;

export default function LLMProviderManager({ variant = 'glassmorphism' }: LLMProviderManagerProps) {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(null);
  const [testingProvider, setTestingProvider] = useState<number | null>(null);
  const [testResults, setTestResults] = useState<Record<number, { success: boolean; error?: string }>>({});

  // Form state
  const [formData, setFormData] = useState<Partial<CreateLLMProviderRequest & { max_input_tokens?: number }>>({
    name: '',
    provider: 'openai',
    api_key: '',
    api_base: '',
    api_version: '',
    default_model_name: '',
    fast_default_model_name: '',
    deployment_name: '',
    default_vision_model: '',
    is_public: true,
    groups: [],
    model_configurations: [],
    max_input_tokens: undefined,
    api_key_changed: true,
  });

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const data = await getLLMProviders();
      setProviders(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load providers');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProvider = async () => {
    try {
      if (!formData.name || !formData.provider || !formData.default_model_name) {
        setError('Name, provider, and default model are required');
        return;
      }

      // Build model configurations with max_input_tokens
      const modelConfigs: ModelConfiguration[] = [
        {
          name: formData.default_model_name,
          is_visible: true,
          max_input_tokens: formData.max_input_tokens,
          api_key: formData.api_key,
          api_base: formData.api_base,
        }
      ];
      
      if (formData.fast_default_model_name) {
        modelConfigs.push({
          name: formData.fast_default_model_name,
          is_visible: true,
          max_input_tokens: formData.max_input_tokens,
          api_key: formData.api_key,
          api_base: formData.api_base,
        });
      }

      const request: CreateLLMProviderRequest = {
        name: formData.name,
        provider: formData.provider,
        api_key: formData.api_key,
        api_base: formData.api_base,
        api_version: formData.api_version,
        custom_config: formData.custom_config,
        default_model_name: formData.default_model_name,
        fast_default_model_name: formData.fast_default_model_name,
        deployment_name: formData.deployment_name,
        is_public: formData.is_public ?? true,
        groups: formData.groups ?? [],
        default_vision_model: formData.default_vision_model,
        model_configurations: modelConfigs,
        api_key_changed: true,
      };

      await createLLMProvider(request);
      await loadProviders();
      setShowCreateForm(false);
      resetForm();
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to create provider');
    }
  };

  const handleUpdateProvider = async () => {
    try {
      if (!editingProvider || !formData.name || !formData.provider || !formData.default_model_name) {
        setError('Name, provider, and default model are required');
        return;
      }

      // Build model configurations with max_input_tokens
      const modelConfigs: ModelConfiguration[] = [
        {
          name: formData.default_model_name,
          is_visible: true,
          max_input_tokens: formData.max_input_tokens,
          api_key: formData.api_key,
          api_base: formData.api_base,
        }
      ];
      
      if (formData.fast_default_model_name) {
        modelConfigs.push({
          name: formData.fast_default_model_name,
          is_visible: true,
          max_input_tokens: formData.max_input_tokens,
          api_key: formData.api_key,
          api_base: formData.api_base,
        });
      }

      const request: CreateLLMProviderRequest = {
        name: formData.name,
        provider: formData.provider,
        api_key: formData.api_key,
        api_base: formData.api_base,
        api_version: formData.api_version,
        custom_config: formData.custom_config,
        default_model_name: formData.default_model_name,
        fast_default_model_name: formData.fast_default_model_name,
        deployment_name: formData.deployment_name,
        is_public: formData.is_public ?? true,
        groups: formData.groups ?? [],
        default_vision_model: formData.default_vision_model,
        model_configurations: modelConfigs,
        api_key_changed: true,
      };

      await updateLLMProvider(request);
      await loadProviders();
      setEditingProvider(null);
      resetForm();
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to update provider');
    }
  };

  const handleDeleteProvider = async (providerId: number) => {
    if (!confirm('Are you sure you want to delete this provider?')) {
      return;
    }

    try {
      await deleteLLMProvider(providerId);
      await loadProviders();
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to delete provider');
    }
  };

  const handleTestProvider = async (provider: LLMProvider) => {
    try {
      setTestingProvider(provider.id);
      setError(null); // Clear any previous errors
      
      // Validation checks before testing
      if (!provider.api_key || provider.api_key.trim() === '') {
        const errorMsg = `❌ ${provider.name}: API Key is required for testing`;
        setError(errorMsg);
        setTestResults(prev => ({ 
          ...prev, 
          [provider.id]: { success: false, error: 'API Key is required' }
        }));
        return;
      }

      if (!provider.default_model_name || provider.default_model_name.trim() === '') {
        const errorMsg = `❌ ${provider.name}: Default model name is required for testing`;
        setError(errorMsg);
        setTestResults(prev => ({ 
          ...prev, 
          [provider.id]: { success: false, error: 'Default model name is required' }
        }));
        return;
      }
      
      console.log('🧪 Testing provider:', provider.name);
      console.log('📋 Provider config:', {
        name: provider.name,
        provider: provider.provider,
        api_base: provider.api_base,
        default_model: provider.default_model_name,
        has_api_key: !!provider.api_key,
      });
      
      const request: TestLLMProviderRequest = {
        name: provider.name,
        provider: provider.provider,
        api_key: provider.api_key,
        api_base: provider.api_base,
        api_version: provider.api_version,
        custom_config: provider.custom_config,
        default_model_name: provider.default_model_name,
        fast_default_model_name: provider.fast_default_model_name,
        deployment_name: provider.deployment_name,
        model_configurations: provider.model_configurations || [],
        api_key_changed: false, // Use existing API key from database for testing
      };

      console.log('📤 Test request payload:', JSON.stringify(request, null, 2));

      const result = await testLLMProvider(request);
      console.log('📥 Test result:', result);
      
      setTestResults(prev => ({ ...prev, [provider.id]: result }));
      
      // Show success/failure message (we'll use error state for notifications)
      if (result.success) {
        setError(`✅ Test successful: ${provider.name} connection is working!`);
        // Auto-clear success message after 3 seconds
        setTimeout(() => setError(null), 3000);
      } else {
        setError(`❌ Test failed for ${provider.name}: ${result.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      // Use console.warn instead of console.error to avoid triggering Next.js error boundary
      console.warn('💥 Test error:', err?.message || 'Unknown error');
      console.warn('Test error details:', err?.status, err?.message);
      let errorMessage = 'Unknown test error';
      
      if (err.status) {
        errorMessage = `HTTP ${err.status}: ${err.message}`;
      } else if (err.message) {
        errorMessage = err.message;
      } else {
        errorMessage = err.toString();
      }
      
      setTestResults(prev => ({ 
        ...prev, 
        [provider.id]: { success: false, error: errorMessage }
      }));
      
      setError(`❌ ${provider.name}: ${errorMessage}`);
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSetDefaultProvider = async (providerId: number) => {
    try {
      await setDefaultProvider(providerId);
      await loadProviders();
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to set default provider');
    }
  };

  const handleEditProvider = (provider: LLMProvider) => {
    setEditingProvider(provider);
    setFormData({
      name: provider.name,
      provider: provider.provider,
      api_key: provider.api_key || '',
      api_base: provider.api_base || '',
      api_version: provider.api_version || '',
      custom_config: provider.custom_config,
      default_model_name: provider.default_model_name,
      fast_default_model_name: provider.fast_default_model_name || '',
      deployment_name: provider.deployment_name || '',
      is_public: provider.is_public,
      groups: provider.groups,
      default_vision_model: provider.default_vision_model || '',
      model_configurations: provider.model_configurations,
      max_input_tokens: provider.model_configurations?.[0]?.max_input_tokens,
      api_key_changed: true,
    });
    setShowCreateForm(true);
  };

  const applyProviderDefaults = (providerType: string) => {
    const defaults = PROVIDER_DEFAULTS[providerType as keyof typeof PROVIDER_DEFAULTS];
    if (defaults) {
      setFormData(prev => ({
        ...prev,
        api_base: defaults.api_base,
        default_model_name: defaults.default_model_name,
        fast_default_model_name: defaults.fast_default_model_name,
        default_vision_model: defaults.default_vision_model,
        max_input_tokens: defaults.max_input_tokens,
        api_version: defaults.api_version || '',
        deployment_name: defaults.deployment_name || '',
      }));
    }
  };

  const resetForm = () => {
    const defaultProvider = 'openai';
    const defaults = PROVIDER_DEFAULTS[defaultProvider];
    
    setFormData({
      name: '',
      provider: defaultProvider,
      api_key: '',
      api_base: defaults.api_base,
      api_version: '',
      default_model_name: defaults.default_model_name,
      fast_default_model_name: defaults.fast_default_model_name,
      deployment_name: '',
      default_vision_model: defaults.default_vision_model,
      is_public: true,
      groups: [],
      model_configurations: [],
      max_input_tokens: defaults.max_input_tokens,
      api_key_changed: true,
    });
  };

  const handleProviderTypeChange = (newProvider: string) => {
    setFormData(prev => ({ ...prev, provider: newProvider }));
    applyProviderDefaults(newProvider);
  };

  const getApiKeyPlaceholder = (provider: string) => {
    const placeholders = {
      openai: 'sk-...',
      anthropic: 'sk-ant-...',
      azure: 'your-azure-api-key',
      bedrock: 'AWS credentials required',
      vertex_ai: 'service-account-key or ADC',
    };
    return placeholders[provider as keyof typeof placeholders] || 'Your API key';
  };

  const getApiKeyHint = (provider: string) => {
    const hints = {
      openai: 'Get your API key from platform.openai.com',
      anthropic: 'Get your API key from console.anthropic.com',
      azure: 'Use your Azure OpenAI resource API key',
      bedrock: 'Configure AWS credentials via environment variables or IAM roles',
      vertex_ai: 'Use service account JSON key or Application Default Credentials',
    };
    return hints[provider as keyof typeof hints] || 'Enter your API credentials';
  };

  const handleCancelForm = () => {
    setShowCreateForm(false);
    setEditingProvider(null);
    resetForm();
    setError(null);
  };

  const getCardClass = () => {
    return cn(
      'p-6 rounded-xl border',
      variant === 'glassmorphism'
        ? 'glass-strong border-white/20'
        : 'neuro-raised bg-white border-gray-200'
    );
  };

  const getButtonClass = (type: 'primary' | 'secondary' | 'danger' = 'secondary') => {
    if (type === 'primary') {
      return cn(
        'px-4 py-2 rounded-lg font-medium transition-all',
        variant === 'glassmorphism'
          ? 'glass-effect text-white hover:glass-strong'
          : 'neuro-pressed bg-blue-500 text-white hover:bg-blue-600'
      );
    }
    if (type === 'danger') {
      return cn(
        'px-4 py-2 rounded-lg font-medium transition-all',
        variant === 'glassmorphism'
          ? 'bg-red-500/20 text-red-200 hover:bg-red-500/30'
          : 'neuro-flat bg-red-50 text-red-600 hover:bg-red-100'
      );
    }
    return cn(
      'px-4 py-2 rounded-lg font-medium transition-all',
      variant === 'glassmorphism'
        ? 'glass-light text-glass hover:glass-effect'
        : 'neuro-flat text-gray-600 hover:neuro-raised'
    );
  };

  const getTextClass = () => {
    return variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800';
  };

  const getSubTextClass = () => {
    return variant === 'glassmorphism' ? 'text-glass opacity-70' : 'text-gray-600';
  };

  if (loading) {
    return (
      <div className={getCardClass()}>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin" />
          <span className={cn('ml-3 text-lg', getTextClass())}>Loading providers...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className={cn('text-2xl font-bold', getTextClass())}>LLM Provider Management</h2>
          <p className={getSubTextClass()}>Manage AI model providers and configurations</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => {
            resetForm();
            setShowCreateForm(true);
          }}
          className={getButtonClass('primary')}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Provider
        </motion.button>
      </div>

      {/* Notification Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={cn(
              'p-4 rounded-lg border flex items-center',
              error.includes('✅') 
                ? variant === 'glassmorphism'
                  ? 'bg-green-500/20 border-green-400/40 text-green-200'
                  : 'bg-green-50 border-green-200 text-green-800'
                : variant === 'glassmorphism'
                  ? 'bg-red-500/20 border-red-400/40 text-red-200'
                  : 'bg-red-50 border-red-200 text-red-800'
            )}
          >
            {error.includes('✅') ? (
              <CheckCircle className="w-5 h-5 mr-3" />
            ) : (
              <AlertCircle className="w-5 h-5 mr-3" />
            )}
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-xs underline opacity-70 hover:opacity-100"
            >
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Provider List */}
      <div className={getCardClass()}>
        <div className="space-y-4">
          {providers.length === 0 ? (
            <div className="text-center py-12">
              <Settings className={cn('w-12 h-12 mx-auto mb-4 opacity-50', getTextClass())} />
              <p className={getTextClass()}>No LLM providers configured</p>
              <p className={getSubTextClass()}>Add your first provider to get started</p>
            </div>
          ) : (
            providers.map((provider) => (
              <motion.div
                key={provider.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  'p-4 rounded-lg border',
                  variant === 'glassmorphism'
                    ? 'glass-light border-white/10'
                    : 'neuro-flat border-gray-200'
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h3 className={cn('text-lg font-semibold', getTextClass())}>
                        {provider.name}
                      </h3>
                      {provider.is_default_provider && (
                        <span className="px-2 py-1 bg-yellow-500/20 text-yellow-600 text-xs rounded-full flex items-center">
                          <Star className="w-3 h-3 mr-1" />
                          Default
                        </span>
                      )}
                    </div>
                    <div className={cn('text-sm mt-1', getSubTextClass())}>
                      <span>Provider: {provider.provider}</span>
                      <span className="mx-2">•</span>
                      <span>Model: {provider.default_model_name}</span>
                      {provider.fast_default_model_name && (
                        <>
                          <span className="mx-2">•</span>
                          <span>Fast: {provider.fast_default_model_name}</span>
                        </>
                      )}
                      {provider.model_configurations?.[0]?.max_input_tokens && (
                        <>
                          <span className="mx-2">•</span>
                          <span>Max Tokens: {provider.model_configurations[0].max_input_tokens}</span>
                        </>
                      )}
                    </div>
                    {provider.api_base && (
                      <div className={cn('text-xs mt-1', getSubTextClass())}>
                        API Base: {provider.api_base}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {/* Test Result */}
                    {testResults[provider.id] && (
                      <div className="flex items-center">
                        {testResults[provider.id].success ? (
                          <div 
                            className="flex items-center px-2 py-1 bg-green-500/20 text-green-600 rounded text-xs"
                            title="Test successful"
                          >
                            <CheckCircle className="w-4 h-4 mr-1" />
                            <span>OK</span>
                          </div>
                        ) : (
                          <div 
                            className="flex items-center px-2 py-1 bg-red-500/20 text-red-600 rounded text-xs max-w-32"
                            title={testResults[provider.id].error}
                          >
                            <XCircle className="w-4 h-4 mr-1" />
                            <span className="truncate">Failed</span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Test Button */}
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => handleTestProvider(provider)}
                      disabled={testingProvider === provider.id}
                      className={cn(
                        'p-2 rounded-lg transition-all',
                        variant === 'glassmorphism'
                          ? 'glass-light text-glass hover:glass-effect'
                          : 'neuro-flat text-gray-600 hover:neuro-raised',
                        testingProvider === provider.id && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      {testingProvider === provider.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <TestTube className="w-4 h-4" />
                      )}
                    </motion.button>

                    {/* Set Default Button */}
                    {!provider.is_default_provider && (
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handleSetDefaultProvider(provider.id)}
                        className={cn(
                          'p-2 rounded-lg transition-all',
                          variant === 'glassmorphism'
                            ? 'glass-light text-glass hover:glass-effect'
                            : 'neuro-flat text-gray-600 hover:neuro-raised'
                        )}
                        title="Set as default"
                      >
                        <Star className="w-4 h-4" />
                      </motion.button>
                    )}

                    {/* Edit Button */}
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => handleEditProvider(provider)}
                      className={cn(
                        'p-2 rounded-lg transition-all',
                        variant === 'glassmorphism'
                          ? 'glass-light text-glass hover:glass-effect'
                          : 'neuro-flat text-gray-600 hover:neuro-raised'
                      )}
                    >
                      <Edit className="w-4 h-4" />
                    </motion.button>

                    {/* Delete Button */}
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => handleDeleteProvider(provider.id)}
                      className={cn(
                        'p-2 rounded-lg transition-all',
                        variant === 'glassmorphism'
                          ? 'bg-red-500/20 text-red-200 hover:bg-red-500/30'
                          : 'neuro-flat bg-red-50 text-red-600 hover:bg-red-100'
                      )}
                    >
                      <Trash2 className="w-4 h-4" />
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* Create/Edit Form Modal */}
      <AnimatePresence>
        {showCreateForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={(e) => e.target === e.currentTarget && handleCancelForm()}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className={cn(
                'w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl p-6',
                variant === 'glassmorphism'
                  ? 'glass-strong border border-white/20'
                  : 'neuro-raised bg-white border border-gray-200'
              )}
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className={cn('text-xl font-semibold', getTextClass())}>
                  {editingProvider ? 'Edit Provider' : 'Create Provider'}
                </h3>
                <button
                  onClick={handleCancelForm}
                  className={cn(
                    'p-2 rounded-lg transition-all',
                    variant === 'glassmorphism'
                      ? 'glass-light text-glass hover:glass-effect'
                      : 'neuro-flat text-gray-600 hover:neuro-raised'
                  )}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                {/* Provider Info */}
                {formData.provider && (
                  <div className={cn(
                    'p-3 rounded-lg border',
                    variant === 'glassmorphism'
                      ? 'bg-blue-500/10 border-blue-400/20 text-blue-200'
                      : 'bg-blue-50 border-blue-200 text-blue-800'
                  )}>
                    <div className="flex items-center">
                      <Settings className="w-4 h-4 mr-2" />
                      <span className="text-sm font-medium">
                        {PROVIDER_TYPES.find(p => p.value === formData.provider)?.label} Configuration
                      </span>
                    </div>
                    <p className="text-xs mt-1 opacity-70">
                      Default values have been pre-filled. Adjust as needed for your setup.
                    </p>
                  </div>
                )}

                {/* Basic Fields */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                      Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      className={cn(
                        'w-full p-3 rounded-lg border',
                        variant === 'glassmorphism'
                          ? 'glass-light border-white/20 text-glass placeholder-glass/50'
                          : 'neuro-flat border-gray-200 text-gray-800'
                      )}
                      placeholder="Provider name"
                    />
                  </div>
                  <div>
                    <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                      Provider Type *
                    </label>
                    <select
                      value={formData.provider || 'openai'}
                      onChange={(e) => handleProviderTypeChange(e.target.value)}
                      className={cn(
                        'w-full p-3 rounded-lg border',
                        variant === 'glassmorphism'
                          ? 'glass-light border-white/20 text-glass'
                          : 'neuro-flat border-gray-200 text-gray-800'
                      )}
                    >
                      {PROVIDER_TYPES.map(type => (
                        <option key={type.value} value={type.value}>{type.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                    API Key
                  </label>
                  <input
                    type="password"
                    value={formData.api_key || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, api_key: e.target.value }))}
                    className={cn(
                      'w-full p-3 rounded-lg border',
                      variant === 'glassmorphism'
                        ? 'glass-light border-white/20 text-glass placeholder-glass/50'
                        : 'neuro-flat border-gray-200 text-gray-800'
                    )}
                    placeholder={getApiKeyPlaceholder(formData.provider || 'openai')}
                  />
                  <p className={cn('text-xs mt-1 opacity-70', getSubTextClass())}>
                    {getApiKeyHint(formData.provider || 'openai')}
                  </p>
                </div>

                <div>
                  <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                    API Base URL
                  </label>
                  <input
                    type="text"
                    value={formData.api_base || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, api_base: e.target.value }))}
                    className={cn(
                      'w-full p-3 rounded-lg border',
                      variant === 'glassmorphism'
                        ? 'glass-light border-white/20 text-glass placeholder-glass/50'
                        : 'neuro-flat border-gray-200 text-gray-800'
                    )}
                    placeholder={formData.api_base || 'API endpoint URL'}
                  />
                  {formData.provider === 'azure' && (
                    <p className={cn('text-xs mt-1 opacity-70', getSubTextClass())}>
                      Replace "your-resource" with your Azure resource name
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                      Default Model *
                    </label>
                    <input
                      type="text"
                      value={formData.default_model_name || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, default_model_name: e.target.value }))}
                      className={cn(
                        'w-full p-3 rounded-lg border',
                        variant === 'glassmorphism'
                          ? 'glass-light border-white/20 text-glass placeholder-glass/50'
                          : 'neuro-flat border-gray-200 text-gray-800'
                      )}
                      placeholder="gpt-3.5-turbo"
                    />
                  </div>
                  <div>
                    <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                      Fast Model
                    </label>
                    <input
                      type="text"
                      value={formData.fast_default_model_name || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, fast_default_model_name: e.target.value }))}
                      className={cn(
                        'w-full p-3 rounded-lg border',
                        variant === 'glassmorphism'
                          ? 'glass-light border-white/20 text-glass placeholder-glass/50'
                          : 'neuro-flat border-gray-200 text-gray-800'
                      )}
                      placeholder="gpt-3.5-turbo"
                    />
                  </div>
                </div>

                {/* Advanced Settings */}
                <div className="space-y-4">
                  <h4 className={cn('text-sm font-medium border-t pt-4', getTextClass())}>
                    Advanced Settings
                  </h4>
                  
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                        Max Tokens
                      </label>
                      <input
                        type="number"
                        value={formData.max_input_tokens || ''}
                        onChange={(e) => setFormData(prev => ({ 
                          ...prev, 
                          max_input_tokens: e.target.value ? parseInt(e.target.value) : undefined 
                        }))}
                        className={cn(
                          'w-full p-3 rounded-lg border',
                          variant === 'glassmorphism'
                            ? 'glass-light border-white/20 text-glass placeholder-glass/50'
                            : 'neuro-flat border-gray-200 text-gray-800'
                        )}
                        placeholder="8192"
                      />
                    </div>
                    <div>
                      <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                        API Version
                      </label>
                      <input
                        type="text"
                        value={formData.api_version || ''}
                        onChange={(e) => setFormData(prev => ({ ...prev, api_version: e.target.value }))}
                        className={cn(
                          'w-full p-3 rounded-lg border',
                          variant === 'glassmorphism'
                            ? 'glass-light border-white/20 text-glass placeholder-glass/50'
                            : 'neuro-flat border-gray-200 text-gray-800'
                        )}
                        placeholder="2023-12-01"
                      />
                    </div>
                    <div>
                      <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                        Deployment
                      </label>
                      <input
                        type="text"
                        value={formData.deployment_name || ''}
                        onChange={(e) => setFormData(prev => ({ ...prev, deployment_name: e.target.value }))}
                        className={cn(
                          'w-full p-3 rounded-lg border',
                          variant === 'glassmorphism'
                            ? 'glass-light border-white/20 text-glass placeholder-glass/50'
                            : 'neuro-flat border-gray-200 text-gray-800'
                        )}
                        placeholder="Azure only"
                      />
                    </div>
                  </div>

                  <div>
                    <label className={cn('block text-sm font-medium mb-2', getTextClass())}>
                      Vision Model
                    </label>
                    <input
                      type="text"
                      value={formData.default_vision_model || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, default_vision_model: e.target.value }))}
                      className={cn(
                        'w-full p-3 rounded-lg border',
                        variant === 'glassmorphism'
                          ? 'glass-light border-white/20 text-glass placeholder-glass/50'
                          : 'neuro-flat border-gray-200 text-gray-800'
                      )}
                      placeholder="gpt-4-vision-preview"
                    />
                  </div>
                </div>

                {/* Public Toggle */}
                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    id="is_public"
                    checked={formData.is_public ?? true}
                    onChange={(e) => setFormData(prev => ({ ...prev, is_public: e.target.checked }))}
                    className="rounded"
                  />
                  <label htmlFor="is_public" className={cn('text-sm', getTextClass())}>
                    Public (available to all users)
                  </label>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end space-x-3 mt-6">
                <button
                  onClick={handleCancelForm}
                  className={getButtonClass('secondary')}
                >
                  Cancel
                </button>
                <button
                  onClick={editingProvider ? handleUpdateProvider : handleCreateProvider}
                  className={getButtonClass('primary')}
                >
                  <Save className="w-4 h-4 mr-2" />
                  {editingProvider ? 'Update' : 'Create'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}