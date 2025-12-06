import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

interface AIModel {
  id: string;
  name: string;
  context_length: number;
  description: string;
}

interface Settings {
  rithmic: {
    username: string;
    password: string;
    server: string;
    gateway: string;
    gateway_url: string;
    is_connected: boolean;
  };
  binance: {
    enabled: boolean;
    selected_symbol: string;
    available_symbols: string[];
    use_testnet: boolean;
    is_connected: boolean;
  };
  openrouter: {
    api_key: string;
    selected_model: string;
    is_connected: boolean;
  };
  active_data_source: string;
  active_symbol: string;
}

// Rithmic gateway options
const RITHMIC_GATEWAYS = [
  { label: 'Test/Paper Trading', value: 'TEST', url: 'rituz00100.rithmic.com:443' },
  { label: 'Chicago (Production)', value: 'CHICAGO', url: '' },
  { label: 'Custom URL', value: 'CUSTOM', url: '' },
];

export default function SettingsScreen() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Rithmic fields
  const [rithmicUsername, setRithmicUsername] = useState('');
  const [rithmicPassword, setRithmicPassword] = useState('');
  const [rithmicServer, setRithmicServer] = useState('Rithmic Paper Trading');
  const [rithmicGateway, setRithmicGateway] = useState('TEST');
  const [rithmicGatewayUrl, setRithmicGatewayUrl] = useState('');
  const [showGatewayPicker, setShowGatewayPicker] = useState(false);
  
  // Binance fields
  const [selectedCrypto, setSelectedCrypto] = useState('BTCUSDT');
  const [cryptoSymbols, setCryptoSymbols] = useState<string[]>([]);
  const [cryptoSearch, setCryptoSearch] = useState('');
  const [showCryptoList, setShowCryptoList] = useState(false);
  
  // OpenRouter fields
  const [openrouterKey, setOpenrouterKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [aiModels, setAiModels] = useState<AIModel[]>([]);
  const [modelSearch, setModelSearch] = useState('');
  const [showModelList, setShowModelList] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);
  
  // Connection status
  const [connectionStatus, setConnectionStatus] = useState<any>(null);

  const fetchSettings = useCallback(async () => {
    try {
      const [settingsRes, statusRes, symbolsRes] = await Promise.all([
        axios.get(`${API_URL}/api/settings`),
        axios.get(`${API_URL}/api/data-source/status`),
        axios.get(`${API_URL}/api/binance/symbols`),
      ]);
      
      const s = settingsRes.data;
      setSettings(s);
      setConnectionStatus(statusRes.data);
      setCryptoSymbols(symbolsRes.data.symbols || []);
      
      // Populate fields
      setRithmicUsername(s.rithmic?.username || '');
      setRithmicPassword(s.rithmic?.password || '');
      setRithmicServer(s.rithmic?.server || 'Rithmic Paper Trading');
      // Handle legacy gateway values
      const gateway = s.rithmic?.gateway || 'TEST';
      const normalizedGateway = gateway.toUpperCase();
      const validGateway = RITHMIC_GATEWAYS.find(g => g.value === normalizedGateway) ? normalizedGateway : 'TEST';
      setRithmicGateway(validGateway);
      setRithmicGatewayUrl(s.rithmic?.gateway_url || '');
      setSelectedCrypto(s.binance?.selected_symbol || 'BTCUSDT');
      setOpenrouterKey(s.openrouter?.api_key || '');
      setSelectedModel(s.openrouter?.selected_model || '');
      
    } catch (error) {
      console.error('Error fetching settings:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAIModels = useCallback(async (forceRefresh = false) => {
    if (!openrouterKey) {
      Alert.alert('API Key Required', 'Please enter your OpenRouter API key first');
      return;
    }
    
    setLoadingModels(true);
    try {
      // First save the API key
      await axios.post(`${API_URL}/api/settings/openrouter`, {
        api_key: openrouterKey,
        selected_model: selectedModel,
        is_connected: false,
      });
      
      // Then fetch models
      const response = await axios.get(`${API_URL}/api/openrouter/models`, {
        params: { refresh: forceRefresh }
      });
      
      setAiModels(response.data.models || []);
      setShowModelList(true);
    } catch (error) {
      console.error('Error fetching models:', error);
      Alert.alert('Error', 'Failed to fetch AI models. Check your API key.');
    } finally {
      setLoadingModels(false);
    }
  }, [openrouterKey, selectedModel]);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const saveRithmicSettings = async () => {
    setSaving(true);
    try {
      await axios.post(`${API_URL}/api/settings/rithmic`, {
        username: rithmicUsername,
        password: rithmicPassword,
        server: rithmicServer,
        gateway: rithmicGateway,
        gateway_url: rithmicGatewayUrl,
        is_connected: false,
      });
      Alert.alert('Success', 'Rithmic credentials saved');
    } catch (error) {
      Alert.alert('Error', 'Failed to save Rithmic settings');
    } finally {
      setSaving(false);
    }
  };

  const saveOpenRouterSettings = async () => {
    setSaving(true);
    try {
      await axios.post(`${API_URL}/api/settings/openrouter`, {
        api_key: openrouterKey,
        selected_model: selectedModel,
        is_connected: Boolean(openrouterKey && selectedModel),
      });
      Alert.alert('Success', 'OpenRouter settings saved');
    } catch (error) {
      Alert.alert('Error', 'Failed to save OpenRouter settings');
    } finally {
      setSaving(false);
    }
  };

  const connectToSource = async (source: string, symbol: string) => {
    setSaving(true);
    try {
      await axios.post(`${API_URL}/api/data-source/connect`, null, {
        params: { source, symbol }
      });
      Alert.alert('Success', `Connected to ${source} for ${symbol}`);
      fetchSettings();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to connect');
    } finally {
      setSaving(false);
    }
  };

  const disconnectSource = async () => {
    setSaving(true);
    try {
      await axios.post(`${API_URL}/api/data-source/disconnect`);
      Alert.alert('Success', 'Disconnected from data source');
      fetchSettings();
    } catch (error) {
      Alert.alert('Error', 'Failed to disconnect');
    } finally {
      setSaving(false);
    }
  };

  const selectModel = async (model: AIModel) => {
    setSelectedModel(model.id);
    setShowModelList(false);
    setModelSearch('');
    
    try {
      await axios.post(`${API_URL}/api/openrouter/set-model`, null, {
        params: { model_id: model.id }
      });
    } catch (error) {
      console.error('Error setting model:', error);
    }
  };

  const filteredModels = aiModels.filter(m => 
    m.name.toLowerCase().includes(modelSearch.toLowerCase()) ||
    m.id.toLowerCase().includes(modelSearch.toLowerCase())
  );

  const filteredSymbols = cryptoSymbols.filter(s =>
    s.toLowerCase().includes(cryptoSearch.toLowerCase())
  );

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#00d4aa" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Text style={styles.title}>Settings</Text>

          {/* Connection Status */}
          <View style={styles.statusCard}>
            <Text style={styles.cardTitle}>Connection Status</Text>
            <View style={styles.statusRow}>
              <View style={styles.statusItem}>
                <View style={[
                  styles.statusDot,
                  { backgroundColor: connectionStatus?.is_streaming ? '#00d4aa' : '#ff4757' }
                ]} />
                <Text style={styles.statusLabel}>
                  {connectionStatus?.is_streaming ? 'Streaming' : 'Disconnected'}
                </Text>
              </View>
              {connectionStatus?.active_symbol && (
                <Text style={styles.activeSymbol}>{connectionStatus.active_symbol}</Text>
              )}
            </View>
            {connectionStatus?.is_streaming && (
              <TouchableOpacity
                style={styles.disconnectButton}
                onPress={disconnectSource}
                disabled={saving}
              >
                <Ionicons name="close-circle" size={16} color="#ff4757" />
                <Text style={styles.disconnectText}>Disconnect</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Binance Settings */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Ionicons name="logo-bitcoin" size={20} color="#f0b90b" />
              <Text style={styles.sectionTitle}>Binance (Crypto)</Text>
            </View>
            
            <Text style={styles.label}>Select Cryptocurrency</Text>
            <TouchableOpacity
              style={styles.dropdown}
              onPress={() => setShowCryptoList(!showCryptoList)}
            >
              <Text style={styles.dropdownText}>{selectedCrypto}</Text>
              <Ionicons name={showCryptoList ? 'chevron-up' : 'chevron-down'} size={20} color="#888" />
            </TouchableOpacity>
            
            {showCryptoList && (
              <View style={styles.listContainer}>
                <TextInput
                  style={styles.searchInput}
                  placeholder="Search symbols..."
                  placeholderTextColor="#666"
                  value={cryptoSearch}
                  onChangeText={setCryptoSearch}
                />
                <ScrollView style={styles.listScroll} nestedScrollEnabled>
                  {filteredSymbols.slice(0, 20).map((symbol) => (
                    <TouchableOpacity
                      key={symbol}
                      style={[
                        styles.listItem,
                        symbol === selectedCrypto && styles.listItemSelected
                      ]}
                      onPress={() => {
                        setSelectedCrypto(symbol);
                        setShowCryptoList(false);
                        setCryptoSearch('');
                      }}
                    >
                      <Text style={styles.listItemText}>{symbol}</Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>
              </View>
            )}
            
            <TouchableOpacity
              style={styles.connectButton}
              onPress={() => connectToSource('binance', selectedCrypto)}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <Ionicons name="flash" size={16} color="#fff" />
                  <Text style={styles.connectButtonText}>Connect to Binance</Text>
                </>
              )}
            </TouchableOpacity>
            
            <Text style={styles.infoText}>
              Binance provides free real-time crypto data. No API key required for market data.
              Note: If connection fails, the app may be running from a geographically restricted region.
              Running locally on your machine should work in most regions.
            </Text>
          </View>

          {/* Rithmic Settings */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Ionicons name="bar-chart" size={20} color="#00d4aa" />
              <Text style={styles.sectionTitle}>Rithmic (XAUUSD)</Text>
            </View>
            
            <Text style={styles.label}>Username</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter Rithmic username"
              placeholderTextColor="#666"
              value={rithmicUsername}
              onChangeText={setRithmicUsername}
              autoCapitalize="none"
            />
            
            <Text style={styles.label}>Password</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter Rithmic password"
              placeholderTextColor="#666"
              value={rithmicPassword}
              onChangeText={setRithmicPassword}
              secureTextEntry
            />
            
            <Text style={styles.label}>Server (System Name)</Text>
            <TextInput
              style={styles.input}
              placeholder="Rithmic Paper Trading"
              placeholderTextColor="#666"
              value={rithmicServer}
              onChangeText={setRithmicServer}
            />
            
            <Text style={styles.label}>Gateway</Text>
            <TouchableOpacity
              style={styles.dropdown}
              onPress={() => setShowGatewayPicker(!showGatewayPicker)}
            >
              <Text style={styles.dropdownText}>
                {RITHMIC_GATEWAYS.find(g => g.value === rithmicGateway)?.label || rithmicGateway}
              </Text>
              <Ionicons name={showGatewayPicker ? 'chevron-up' : 'chevron-down'} size={20} color="#888" />
            </TouchableOpacity>
            
            {showGatewayPicker && (
              <View style={styles.listContainer}>
                {RITHMIC_GATEWAYS.map((gw) => (
                  <TouchableOpacity
                    key={gw.value}
                    style={[
                      styles.listItem,
                      gw.value === rithmicGateway && styles.listItemSelected
                    ]}
                    onPress={() => {
                      setRithmicGateway(gw.value);
                      if (gw.url) setRithmicGatewayUrl(gw.url);
                      setShowGatewayPicker(false);
                    }}
                  >
                    <Text style={styles.listItemText}>{gw.label}</Text>
                    {gw.url && <Text style={styles.modelId}>{gw.url}</Text>}
                  </TouchableOpacity>
                ))}
              </View>
            )}
            
            {rithmicGateway === 'CUSTOM' && (
              <>
                <Text style={styles.label}>Gateway URL</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g., rituz00100.rithmic.com:443"
                  placeholderTextColor="#666"
                  value={rithmicGatewayUrl}
                  onChangeText={setRithmicGatewayUrl}
                  autoCapitalize="none"
                />
              </>
            )}
            
            <View style={styles.buttonRow}>
              <TouchableOpacity
                style={[styles.saveButton, { flex: 1, marginRight: 8 }]}
                onPress={saveRithmicSettings}
                disabled={saving}
              >
                <Text style={styles.saveButtonText}>Save</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.connectButton, { flex: 1 }]}
                onPress={() => connectToSource('rithmic', 'XAUUSD')}
                disabled={saving || !rithmicUsername}
              >
                <Text style={styles.connectButtonText}>Connect</Text>
              </TouchableOpacity>
            </View>
            
            <Text style={styles.infoText}>
              Rithmic integration uses the async_rithmic library. You need valid Rithmic credentials
              from your broker. For testing, use the Test/Paper Trading gateway. Production access
              requires passing Rithmic's conformance test. Without credentials, XAUUSD data is simulated.
            </Text>
            <Text style={[styles.infoText, { marginTop: 8, color: '#5352ed' }]}>
              Get Rithmic access: Contact your futures broker or visit rithmic.com/apis
            </Text>
          </View>

          {/* OpenRouter Settings */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Ionicons name="sparkles" size={20} color="#5352ed" />
              <Text style={styles.sectionTitle}>OpenRouter AI</Text>
            </View>
            
            <Text style={styles.label}>API Key</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter OpenRouter API key"
              placeholderTextColor="#666"
              value={openrouterKey}
              onChangeText={setOpenrouterKey}
              autoCapitalize="none"
              secureTextEntry
            />
            
            <Text style={styles.label}>AI Model</Text>
            <TouchableOpacity
              style={styles.dropdown}
              onPress={() => fetchAIModels()}
            >
              <Text style={styles.dropdownText} numberOfLines={1}>
                {selectedModel || 'Select AI Model'}
              </Text>
              {loadingModels ? (
                <ActivityIndicator size="small" color="#888" />
              ) : (
                <Ionicons name="chevron-down" size={20} color="#888" />
              )}
            </TouchableOpacity>
            
            {showModelList && (
              <View style={styles.listContainer}>
                <TextInput
                  style={styles.searchInput}
                  placeholder="Search models..."
                  placeholderTextColor="#666"
                  value={modelSearch}
                  onChangeText={setModelSearch}
                />
                <ScrollView style={styles.modelListScroll} nestedScrollEnabled>
                  {filteredModels.slice(0, 30).map((model) => (
                    <TouchableOpacity
                      key={model.id}
                      style={[
                        styles.modelItem,
                        model.id === selectedModel && styles.listItemSelected
                      ]}
                      onPress={() => selectModel(model)}
                    >
                      <Text style={styles.modelName}>{model.name}</Text>
                      <Text style={styles.modelId}>{model.id}</Text>
                      {model.context_length > 0 && (
                        <Text style={styles.modelContext}>
                          Context: {(model.context_length / 1000).toFixed(0)}K
                        </Text>
                      )}
                    </TouchableOpacity>
                  ))}
                </ScrollView>
                <TouchableOpacity
                  style={styles.refreshButton}
                  onPress={() => fetchAIModels(true)}
                >
                  <Ionicons name="refresh" size={16} color="#5352ed" />
                  <Text style={styles.refreshText}>Refresh Models</Text>
                </TouchableOpacity>
              </View>
            )}
            
            <TouchableOpacity
              style={[styles.saveButton, { marginTop: 12 }]}
              onPress={saveOpenRouterSettings}
              disabled={saving}
            >
              <Ionicons name="save" size={16} color="#fff" />
              <Text style={styles.saveButtonText}>Save OpenRouter Settings</Text>
            </TouchableOpacity>
            
            <Text style={styles.infoText}>
              Get your API key from openrouter.ai. The AI provides real-time
              order flow analysis and trading insights.
            </Text>
          </View>

          {/* Simulated Data */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Ionicons name="flask" size={20} color="#ffa502" />
              <Text style={styles.sectionTitle}>Simulated Data</Text>
            </View>
            
            <Text style={styles.infoText}>
              Test the signal engine with simulated market data.
              No credentials required.
            </Text>
            
            <TouchableOpacity
              style={[styles.connectButton, { backgroundColor: '#ffa502' }]}
              onPress={() => connectToSource('simulated', 'SIMULATED')}
              disabled={saving}
            >
              <Ionicons name="play" size={16} color="#fff" />
              <Text style={styles.connectButtonText}>Start Simulation</Text>
            </TouchableOpacity>
          </View>

        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0f',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollContent: {
    padding: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
  },
  statusCard: {
    backgroundColor: '#12121a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#888',
    marginBottom: 12,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 8,
  },
  statusLabel: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  activeSymbol: {
    color: '#00d4aa',
    fontSize: 14,
    fontWeight: '600',
  },
  disconnectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#ff475720',
  },
  disconnectText: {
    color: '#ff4757',
    fontSize: 14,
    marginLeft: 6,
  },
  section: {
    backgroundColor: '#12121a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginLeft: 8,
  },
  label: {
    color: '#888',
    fontSize: 12,
    marginBottom: 6,
    marginTop: 8,
  },
  input: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 12,
    color: '#fff',
    fontSize: 14,
  },
  dropdown: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  dropdownText: {
    color: '#fff',
    fontSize: 14,
    flex: 1,
  },
  listContainer: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    marginTop: 8,
    overflow: 'hidden',
  },
  searchInput: {
    backgroundColor: '#252540',
    padding: 12,
    color: '#fff',
    fontSize: 14,
  },
  listScroll: {
    maxHeight: 200,
  },
  modelListScroll: {
    maxHeight: 300,
  },
  listItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#252540',
  },
  listItemSelected: {
    backgroundColor: '#5352ed20',
  },
  listItemText: {
    color: '#fff',
    fontSize: 14,
  },
  modelItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#252540',
  },
  modelName: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  modelId: {
    color: '#666',
    fontSize: 11,
    marginTop: 2,
  },
  modelContext: {
    color: '#5352ed',
    fontSize: 10,
    marginTop: 4,
  },
  refreshButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: '#252540',
  },
  refreshText: {
    color: '#5352ed',
    fontSize: 13,
    marginLeft: 6,
  },
  buttonRow: {
    flexDirection: 'row',
    marginTop: 12,
  },
  saveButton: {
    backgroundColor: '#5352ed',
    borderRadius: 8,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  connectButton: {
    backgroundColor: '#00d4aa',
    borderRadius: 8,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
  },
  connectButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  infoText: {
    color: '#666',
    fontSize: 12,
    marginTop: 12,
    lineHeight: 18,
  },
});
