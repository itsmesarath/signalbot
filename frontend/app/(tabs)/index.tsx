import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';
const { width } = Dimensions.get('window');

interface Signal {
  signal_type: string;
  hfss_score: number;
  probability_buy: number;
  probability_sell: number;
  probability_no_trade: number;
  confidence: number;
  reason: string;
  price_at_signal: number;
  timestamp?: string;
}

interface Metrics {
  delta: {
    raw_delta: number;
    normalized_delta: number;
    cumulative_delta: number;
  };
  absorption: {
    score: number;
    strength: number;
    bid_absorption: number;
    ask_absorption: number;
  };
  iceberg: {
    probability: number;
    fill_to_display_ratio: number;
  };
  momentum: {
    ofmbi: number;
    tape_speed: number;
    volume_velocity: number;
  };
  structure: {
    regime: string;
    trend_direction: string;
    bos_detected: boolean;
    choch_detected: boolean;
  };
}

interface ConnectionStatus {
  is_streaming: boolean;
  binance_connected: boolean;
  rithmic_connected: boolean;
  active_symbol: string | null;
  active_source: string | null;
}

export default function Dashboard() {
  const [signal, setSignal] = useState<Signal | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastPrice, setLastPrice] = useState<number>(0);
  const [priceChange, setPriceChange] = useState<'up' | 'down' | 'none'>('none');
  const wsRef = useRef<WebSocket | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [signalRes, metricsRes, statusRes] = await Promise.all([
        axios.get(`${API_URL}/api/signals/current`),
        axios.get(`${API_URL}/api/metrics`),
        axios.get(`${API_URL}/api/data-source/status`),
      ]);
      
      setSignal(signalRes.data);
      setMetrics(metricsRes.data);
      setStatus(statusRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    const wsUrl = API_URL.replace('http', 'ws') + '/api/ws';
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'trade') {
          const newPrice = data.data.price;
          if (lastPrice > 0) {
            setPriceChange(newPrice > lastPrice ? 'up' : newPrice < lastPrice ? 'down' : 'none');
          }
          setLastPrice(newPrice);
        } else if (data.type === 'signal') {
          setSignal(data.data);
        } else if (data.type === 'metrics') {
          setMetrics(data.data);
        }
      } catch (e) {
        // Ignore parse errors
      }
    };
    
    ws.onerror = (error) => {
      console.log('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('WebSocket closed, reconnecting...');
      setTimeout(connectWebSocket, 3000);
    };
    
    wsRef.current = ws;
  }, [lastPrice]);

  useEffect(() => {
    fetchData();
    connectWebSocket();
    
    const interval = setInterval(fetchData, 5000);
    
    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, [fetchData]);

  const getSignalColor = (type: string) => {
    switch (type) {
      case 'buy': return '#00d4aa';
      case 'sell': return '#ff4757';
      default: return '#ffa502';
    }
  };

  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'buy': return 'trending-up';
      case 'sell': return 'trending-down';
      default: return 'remove';
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#00d4aa" />
          <Text style={styles.loadingText}>Loading HFT Dashboard...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#00d4aa"
          />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>HFT Signal Generator</Text>
          <View style={styles.connectionStatus}>
            <View style={[
              styles.statusDot,
              { backgroundColor: status?.is_streaming ? '#00d4aa' : '#ff4757' }
            ]} />
            <Text style={styles.statusText}>
              {status?.active_symbol || 'Disconnected'}
            </Text>
          </View>
        </View>

        {/* Price Display */}
        <View style={styles.priceCard}>
          <Text style={styles.priceLabel}>
            {status?.active_symbol || 'BTCUSDT'}
          </Text>
          <View style={styles.priceRow}>
            <Text style={[
              styles.priceValue,
              priceChange === 'up' && styles.priceUp,
              priceChange === 'down' && styles.priceDown,
            ]}>
              {lastPrice > 0 ? lastPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '---'}
            </Text>
            <Ionicons
              name={priceChange === 'up' ? 'caret-up' : priceChange === 'down' ? 'caret-down' : 'remove'}
              size={24}
              color={priceChange === 'up' ? '#00d4aa' : priceChange === 'down' ? '#ff4757' : '#666'}
            />
          </View>
        </View>

        {/* Signal Card */}
        <View style={styles.signalCard}>
          <View style={styles.signalHeader}>
            <Text style={styles.cardTitle}>Current Signal</Text>
            <View style={[
              styles.signalBadge,
              { backgroundColor: getSignalColor(signal?.signal_type || 'no_trade') + '20' }
            ]}>
              <Ionicons
                name={getSignalIcon(signal?.signal_type || 'no_trade') as any}
                size={20}
                color={getSignalColor(signal?.signal_type || 'no_trade')}
              />
              <Text style={[
                styles.signalText,
                { color: getSignalColor(signal?.signal_type || 'no_trade') }
              ]}>
                {(signal?.signal_type || 'NO TRADE').toUpperCase()}
              </Text>
            </View>
          </View>
          
          {/* Probability Bars */}
          <View style={styles.probContainer}>
            <View style={styles.probRow}>
              <Text style={styles.probLabel}>Buy</Text>
              <View style={styles.probBarBg}>
                <View style={[
                  styles.probBar,
                  { width: `${(signal?.probability_buy || 0) * 100}%`, backgroundColor: '#00d4aa' }
                ]} />
              </View>
              <Text style={styles.probValue}>{((signal?.probability_buy || 0) * 100).toFixed(1)}%</Text>
            </View>
            <View style={styles.probRow}>
              <Text style={styles.probLabel}>Sell</Text>
              <View style={styles.probBarBg}>
                <View style={[
                  styles.probBar,
                  { width: `${(signal?.probability_sell || 0) * 100}%`, backgroundColor: '#ff4757' }
                ]} />
              </View>
              <Text style={styles.probValue}>{((signal?.probability_sell || 0) * 100).toFixed(1)}%</Text>
            </View>
            <View style={styles.probRow}>
              <Text style={styles.probLabel}>Hold</Text>
              <View style={styles.probBarBg}>
                <View style={[
                  styles.probBar,
                  { width: `${(signal?.probability_no_trade || 0) * 100}%`, backgroundColor: '#ffa502' }
                ]} />
              </View>
              <Text style={styles.probValue}>{((signal?.probability_no_trade || 0) * 100).toFixed(1)}%</Text>
            </View>
          </View>

          {/* HFSS Score */}
          <View style={styles.hfssContainer}>
            <Text style={styles.hfssLabel}>HFSS Score</Text>
            <Text style={[
              styles.hfssValue,
              { color: (signal?.hfss_score || 0) > 0 ? '#00d4aa' : (signal?.hfss_score || 0) < 0 ? '#ff4757' : '#fff' }
            ]}>
              {(signal?.hfss_score || 0).toFixed(4)}
            </Text>
          </View>

          {/* Reason */}
          {signal?.reason && (
            <Text style={styles.reasonText}>{signal.reason}</Text>
          )}
        </View>

        {/* Metrics Grid */}
        <Text style={styles.sectionTitle}>Order Flow Metrics</Text>
        <View style={styles.metricsGrid}>
          {/* Delta */}
          <View style={styles.metricCard}>
            <Ionicons name="swap-vertical" size={20} color="#00d4aa" />
            <Text style={styles.metricLabel}>Delta</Text>
            <Text style={[
              styles.metricValue,
              { color: (metrics?.delta?.normalized_delta || 0) > 0 ? '#00d4aa' : '#ff4757' }
            ]}>
              {(metrics?.delta?.normalized_delta || 0).toFixed(3)}
            </Text>
            <Text style={styles.metricSub}>Cumulative: {(metrics?.delta?.cumulative_delta || 0).toFixed(0)}</Text>
          </View>

          {/* Absorption */}
          <View style={styles.metricCard}>
            <Ionicons name="shield" size={20} color="#ffa502" />
            <Text style={styles.metricLabel}>Absorption</Text>
            <Text style={styles.metricValue}>
              {((metrics?.absorption?.strength || 0) * 100).toFixed(1)}%
            </Text>
            <Text style={styles.metricSub}>
              Bid: {((metrics?.absorption?.bid_absorption || 0) * 100).toFixed(0)}% | Ask: {((metrics?.absorption?.ask_absorption || 0) * 100).toFixed(0)}%
            </Text>
          </View>

          {/* Iceberg */}
          <View style={styles.metricCard}>
            <Ionicons name="eye-off" size={20} color="#5352ed" />
            <Text style={styles.metricLabel}>Iceberg</Text>
            <Text style={styles.metricValue}>
              {((metrics?.iceberg?.probability || 0) * 100).toFixed(1)}%
            </Text>
            <Text style={styles.metricSub}>FDR: {(metrics?.iceberg?.fill_to_display_ratio || 0).toFixed(2)}</Text>
          </View>

          {/* Momentum */}
          <View style={styles.metricCard}>
            <Ionicons name="speedometer" size={20} color="#ff6b81" />
            <Text style={styles.metricLabel}>OFMBI</Text>
            <Text style={[
              styles.metricValue,
              { color: (metrics?.momentum?.ofmbi || 0) > 0 ? '#00d4aa' : '#ff4757' }
            ]}>
              {(metrics?.momentum?.ofmbi || 0).toFixed(2)}
            </Text>
            <Text style={styles.metricSub}>Tape: {(metrics?.momentum?.tape_speed || 0).toFixed(1)}/s</Text>
          </View>
        </View>

        {/* Structure Info */}
        <View style={styles.structureCard}>
          <View style={styles.structureRow}>
            <View style={styles.structureItem}>
              <Text style={styles.structureLabel}>Regime</Text>
              <Text style={styles.structureValue}>{metrics?.structure?.regime || 'N/A'}</Text>
            </View>
            <View style={styles.structureItem}>
              <Text style={styles.structureLabel}>Trend</Text>
              <Text style={[
                styles.structureValue,
                { color: metrics?.structure?.trend_direction === 'up' ? '#00d4aa' : metrics?.structure?.trend_direction === 'down' ? '#ff4757' : '#fff' }
              ]}>
                {metrics?.structure?.trend_direction?.toUpperCase() || 'N/A'}
              </Text>
            </View>
          </View>
          <View style={styles.structureRow}>
            <View style={styles.structureItem}>
              <Text style={styles.structureLabel}>BOS</Text>
              <View style={[
                styles.indicator,
                { backgroundColor: metrics?.structure?.bos_detected ? '#00d4aa' : '#333' }
              ]} />
            </View>
            <View style={styles.structureItem}>
              <Text style={styles.structureLabel}>CHOCH</Text>
              <View style={[
                styles.indicator,
                { backgroundColor: metrics?.structure?.choch_detected ? '#ff4757' : '#333' }
              ]} />
            </View>
          </View>
        </View>

      </ScrollView>
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
  loadingText: {
    color: '#888',
    marginTop: 16,
    fontSize: 16,
  },
  scrollContent: {
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  connectionStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a2e',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  priceCard: {
    backgroundColor: '#12121a',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    alignItems: 'center',
  },
  priceLabel: {
    color: '#888',
    fontSize: 14,
    marginBottom: 4,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  priceValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#fff',
    marginRight: 8,
  },
  priceUp: {
    color: '#00d4aa',
  },
  priceDown: {
    color: '#ff4757',
  },
  signalCard: {
    backgroundColor: '#12121a',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
  },
  signalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  signalBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  signalText: {
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 6,
  },
  probContainer: {
    marginBottom: 16,
  },
  probRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  probLabel: {
    width: 40,
    color: '#888',
    fontSize: 12,
  },
  probBarBg: {
    flex: 1,
    height: 8,
    backgroundColor: '#1a1a2e',
    borderRadius: 4,
    marginHorizontal: 8,
    overflow: 'hidden',
  },
  probBar: {
    height: '100%',
    borderRadius: 4,
  },
  probValue: {
    width: 50,
    color: '#fff',
    fontSize: 12,
    textAlign: 'right',
  },
  hfssContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#1a1a2e',
    paddingTop: 12,
    marginTop: 4,
  },
  hfssLabel: {
    color: '#888',
    fontSize: 14,
  },
  hfssValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  reasonText: {
    color: '#888',
    fontSize: 12,
    marginTop: 12,
    fontStyle: 'italic',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 12,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  metricCard: {
    width: (width - 48) / 2,
    backgroundColor: '#12121a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    alignItems: 'center',
  },
  metricLabel: {
    color: '#888',
    fontSize: 12,
    marginTop: 8,
  },
  metricValue: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 4,
  },
  metricSub: {
    color: '#666',
    fontSize: 10,
    marginTop: 4,
  },
  structureCard: {
    backgroundColor: '#12121a',
    borderRadius: 16,
    padding: 16,
  },
  structureRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 12,
  },
  structureItem: {
    alignItems: 'center',
  },
  structureLabel: {
    color: '#888',
    fontSize: 12,
    marginBottom: 4,
  },
  structureValue: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  indicator: {
    width: 24,
    height: 24,
    borderRadius: 12,
  },
});
