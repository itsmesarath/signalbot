import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

interface Signal {
  id: string;
  symbol: string;
  signal_type: string;
  hfss_score: number;
  probability_buy: number;
  probability_sell: number;
  confidence: number;
  reason: string;
  price_at_signal: number;
  timestamp: string;
  ai_analysis?: string;
}

export default function SignalsScreen() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<string>('');

  const fetchSignals = useCallback(async () => {
    try {
      const params: any = { limit: 100 };
      if (filter) params.signal_type = filter;
      
      const response = await axios.get(`${API_URL}/api/signals/history`, { params });
      setSignals(response.data.signals || []);
    } catch (error) {
      console.error('Error fetching signals:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 10000);
    return () => clearInterval(interval);
  }, [fetchSignals]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchSignals();
  }, [fetchSignals]);

  const requestAIAnalysis = async () => {
    setAnalyzing(true);
    try {
      const response = await axios.post(`${API_URL}/api/ai/analyze`);
      setAiAnalysis(response.data.analysis || 'No analysis available');
    } catch (error: any) {
      setAiAnalysis(error.response?.data?.detail || 'AI analysis failed. Configure OpenRouter in settings.');
    } finally {
      setAnalyzing(false);
    }
  };

  const getSignalColor = (type: string) => {
    switch (type) {
      case 'buy': return '#00d4aa';
      case 'sell': return '#ff4757';
      default: return '#ffa502';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const renderSignal = ({ item }: { item: Signal }) => (
    <View style={styles.signalCard}>
      <View style={styles.signalRow}>
        <View style={[
          styles.signalTypeBadge,
          { backgroundColor: getSignalColor(item.signal_type) + '20' }
        ]}>
          <Ionicons
            name={item.signal_type === 'buy' ? 'trending-up' : item.signal_type === 'sell' ? 'trending-down' : 'remove'}
            size={16}
            color={getSignalColor(item.signal_type)}
          />
          <Text style={[styles.signalTypeText, { color: getSignalColor(item.signal_type) }]}>
            {item.signal_type.toUpperCase()}
          </Text>
        </View>
        <Text style={styles.signalTime}>{formatTime(item.timestamp)}</Text>
      </View>
      
      <View style={styles.signalDetails}>
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Symbol</Text>
          <Text style={styles.detailValue}>{item.symbol}</Text>
        </View>
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Price</Text>
          <Text style={styles.detailValue}>
            {item.price_at_signal?.toLocaleString(undefined, { minimumFractionDigits: 2 }) || 'N/A'}
          </Text>
        </View>
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>HFSS</Text>
          <Text style={[
            styles.detailValue,
            { color: item.hfss_score > 0 ? '#00d4aa' : item.hfss_score < 0 ? '#ff4757' : '#fff' }
          ]}>
            {item.hfss_score?.toFixed(4) || 'N/A'}
          </Text>
        </View>
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Confidence</Text>
          <Text style={styles.detailValue}>{((item.confidence || 0) * 100).toFixed(1)}%</Text>
        </View>
      </View>
      
      {item.reason && (
        <Text style={styles.reasonText}>{item.reason}</Text>
      )}
    </View>
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
      <View style={styles.header}>
        <Text style={styles.title}>Signal History</Text>
        <TouchableOpacity
          style={styles.aiButton}
          onPress={requestAIAnalysis}
          disabled={analyzing}
        >
          {analyzing ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <>
              <Ionicons name="bulb" size={16} color="#fff" />
              <Text style={styles.aiButtonText}>AI Insight</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {aiAnalysis ? (
        <View style={styles.aiCard}>
          <View style={styles.aiHeader}>
            <Ionicons name="sparkles" size={16} color="#ffa502" />
            <Text style={styles.aiTitle}>AI Analysis</Text>
            <TouchableOpacity onPress={() => setAiAnalysis('')}>
              <Ionicons name="close" size={20} color="#666" />
            </TouchableOpacity>
          </View>
          <Text style={styles.aiText}>{aiAnalysis}</Text>
        </View>
      ) : null}

      {/* Filters */}
      <View style={styles.filters}>
        <TouchableOpacity
          style={[styles.filterButton, !filter && styles.filterActive]}
          onPress={() => setFilter(null)}
        >
          <Text style={[styles.filterText, !filter && styles.filterTextActive]}>All</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterButton, filter === 'buy' && styles.filterActiveBuy]}
          onPress={() => setFilter('buy')}
        >
          <Text style={[styles.filterText, filter === 'buy' && styles.filterTextActive]}>Buy</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterButton, filter === 'sell' && styles.filterActiveSell]}
          onPress={() => setFilter('sell')}
        >
          <Text style={[styles.filterText, filter === 'sell' && styles.filterTextActive]}>Sell</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterButton, filter === 'no_trade' && styles.filterActiveHold]}
          onPress={() => setFilter('no_trade')}
        >
          <Text style={[styles.filterText, filter === 'no_trade' && styles.filterTextActive]}>Hold</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={signals}
        keyExtractor={(item) => item.id || item.timestamp}
        renderItem={renderSignal}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#00d4aa"
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="pulse" size={48} color="#333" />
            <Text style={styles.emptyText}>No signals yet</Text>
            <Text style={styles.emptySubtext}>Connect to a data source to start generating signals</Text>
          </View>
        }
      />
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  aiButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#5352ed',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
  },
  aiButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 4,
  },
  aiCard: {
    backgroundColor: '#1a1a2e',
    margin: 16,
    marginTop: 0,
    padding: 12,
    borderRadius: 12,
    borderLeftWidth: 3,
    borderLeftColor: '#ffa502',
  },
  aiHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  aiTitle: {
    color: '#ffa502',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
    flex: 1,
  },
  aiText: {
    color: '#ccc',
    fontSize: 13,
    lineHeight: 20,
  },
  filters: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#1a1a2e',
    marginRight: 8,
  },
  filterActive: {
    backgroundColor: '#5352ed',
  },
  filterActiveBuy: {
    backgroundColor: '#00d4aa',
  },
  filterActiveSell: {
    backgroundColor: '#ff4757',
  },
  filterActiveHold: {
    backgroundColor: '#ffa502',
  },
  filterText: {
    color: '#888',
    fontSize: 13,
    fontWeight: '600',
  },
  filterTextActive: {
    color: '#fff',
  },
  listContent: {
    padding: 16,
    paddingTop: 0,
  },
  signalCard: {
    backgroundColor: '#12121a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  signalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  signalTypeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  signalTypeText: {
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 4,
  },
  signalTime: {
    color: '#666',
    fontSize: 12,
  },
  signalDetails: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 12,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  detailLabel: {
    color: '#888',
    fontSize: 12,
  },
  detailValue: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  reasonText: {
    color: '#888',
    fontSize: 11,
    marginTop: 12,
    fontStyle: 'italic',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    color: '#666',
    fontSize: 18,
    marginTop: 16,
  },
  emptySubtext: {
    color: '#444',
    fontSize: 14,
    marginTop: 8,
    textAlign: 'center',
  },
});
