import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';
const { width } = Dimensions.get('window');

interface OrderBookLevel {
  price: number;
  quantity: number;
}

interface OrderBookData {
  symbol: string;
  best_bid: number;
  best_ask: number;
  spread: number;
  mid_price: number;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  timestamp: string;
}

interface Trade {
  price: number;
  quantity: number;
  side: string;
  timestamp: string;
}

export default function OrderbookScreen() {
  const [orderBook, setOrderBook] = useState<OrderBookData | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [connected, setConnected] = useState(false);
  const [symbol, setSymbol] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const maxQuantity = useRef(0);

  const connectWebSocket = useCallback(() => {
    const wsUrl = API_URL.replace('http', 'ws') + '/api/ws';
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('DOM WebSocket connected');
      setConnected(true);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'orderbook') {
          setOrderBook(data.data);
          setSymbol(data.data.symbol);
          
          // Update max quantity for scaling bars
          const allQuantities = [
            ...data.data.bids.map((b: OrderBookLevel) => b.quantity),
            ...data.data.asks.map((a: OrderBookLevel) => a.quantity)
          ];
          maxQuantity.current = Math.max(...allQuantities, 1);
        } else if (data.type === 'trade') {
          setTrades(prev => [data.data, ...prev.slice(0, 49)]);
        } else if (data.type === 'connection') {
          setConnected(data.data.connected);
          setSymbol(data.data.symbol);
        }
      } catch (e) {
        // Ignore parse errors
      }
    };
    
    ws.onerror = () => {
      setConnected(false);
    };
    
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connectWebSocket, 3000);
    };
    
    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  const formatPrice = (price: number) => {
    if (price > 1000) return price.toFixed(2);
    if (price > 1) return price.toFixed(4);
    return price.toFixed(6);
  };

  const formatQuantity = (qty: number) => {
    if (qty >= 1000000) return (qty / 1000000).toFixed(2) + 'M';
    if (qty >= 1000) return (qty / 1000).toFixed(2) + 'K';
    return qty.toFixed(4);
  };

  const getBarWidth = (quantity: number) => {
    return `${Math.min((quantity / maxQuantity.current) * 100, 100)}%`;
  };

  const renderDOMLevel = (level: OrderBookLevel, side: 'bid' | 'ask', index: number) => {
    const barColor = side === 'bid' ? '#00d4aa20' : '#ff475720';
    const textColor = side === 'bid' ? '#00d4aa' : '#ff4757';
    const barWidth = getBarWidth(level.quantity);

    return (
      <View key={`${side}-${index}`} style={styles.domRow}>
        {side === 'bid' ? (
          <>
            <View style={styles.domQuantityContainer}>
              <View style={[styles.domBar, styles.domBarBid, { width: barWidth, backgroundColor: barColor }]} />
              <Text style={styles.domQuantity}>{formatQuantity(level.quantity)}</Text>
            </View>
            <Text style={[styles.domPrice, { color: textColor }]}>{formatPrice(level.price)}</Text>
          </>
        ) : (
          <>
            <Text style={[styles.domPrice, { color: textColor }]}>{formatPrice(level.price)}</Text>
            <View style={styles.domQuantityContainer}>
              <View style={[styles.domBar, styles.domBarAsk, { width: barWidth, backgroundColor: barColor }]} />
              <Text style={[styles.domQuantity, { textAlign: 'right' }]}>{formatQuantity(level.quantity)}</Text>
            </View>
          </>
        )}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Depth of Market</Text>
        <View style={styles.connectionBadge}>
          <View style={[styles.statusDot, { backgroundColor: connected ? '#00d4aa' : '#ff4757' }]} />
          <Text style={styles.symbolText}>{symbol || 'Disconnected'}</Text>
        </View>
      </View>

      {/* Spread Info */}
      {orderBook && (
        <View style={styles.spreadCard}>
          <View style={styles.spreadItem}>
            <Text style={styles.spreadLabel}>Best Bid</Text>
            <Text style={[styles.spreadValue, { color: '#00d4aa' }]}>
              {formatPrice(orderBook.best_bid)}
            </Text>
          </View>
          <View style={styles.spreadItem}>
            <Text style={styles.spreadLabel}>Spread</Text>
            <Text style={styles.spreadValue}>
              {formatPrice(orderBook.spread)}
            </Text>
          </View>
          <View style={styles.spreadItem}>
            <Text style={styles.spreadLabel}>Best Ask</Text>
            <Text style={[styles.spreadValue, { color: '#ff4757' }]}>
              {formatPrice(orderBook.best_ask)}
            </Text>
          </View>
        </View>
      )}

      <View style={styles.content}>
        {/* DOM Ladder */}
        <View style={styles.domContainer}>
          <View style={styles.domHeader}>
            <Text style={styles.domHeaderText}>BIDS</Text>
            <Text style={styles.domHeaderText}>PRICE</Text>
            <Text style={styles.domHeaderText}>ASKS</Text>
          </View>
          
          <ScrollView style={styles.domScroll}>
            {/* Asks (reversed so lowest ask is at bottom) */}
            {orderBook?.asks.slice().reverse().map((ask, i) => 
              renderDOMLevel(ask, 'ask', i)
            )}
            
            {/* Spread separator */}
            <View style={styles.spreadSeparator}>
              <Text style={styles.spreadSeparatorText}>
                SPREAD: {orderBook ? formatPrice(orderBook.spread) : '---'}
              </Text>
            </View>
            
            {/* Bids */}
            {orderBook?.bids.map((bid, i) => 
              renderDOMLevel(bid, 'bid', i)
            )}
          </ScrollView>
        </View>

        {/* Time & Sales */}
        <View style={styles.tapeContainer}>
          <Text style={styles.tapeTitle}>Time & Sales</Text>
          <ScrollView style={styles.tapeScroll}>
            {trades.map((trade, i) => (
              <View key={i} style={styles.tradeRow}>
                <Text style={[
                  styles.tradePrice,
                  { color: trade.side === 'buy' ? '#00d4aa' : '#ff4757' }
                ]}>
                  {formatPrice(trade.price)}
                </Text>
                <Text style={styles.tradeQty}>{formatQuantity(trade.quantity)}</Text>
                <Ionicons
                  name={trade.side === 'buy' ? 'arrow-up' : 'arrow-down'}
                  size={12}
                  color={trade.side === 'buy' ? '#00d4aa' : '#ff4757'}
                />
              </View>
            ))}
            {trades.length === 0 && (
              <Text style={styles.emptyTape}>No trades yet</Text>
            )}
          </ScrollView>
        </View>
      </View>

      {!connected && (
        <View style={styles.disconnectedOverlay}>
          <ActivityIndicator size="large" color="#00d4aa" />
          <Text style={styles.disconnectedText}>Connecting to data feed...</Text>
          <Text style={styles.disconnectedSubtext}>Go to Settings to connect to a data source</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0f',
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
  connectionBadge: {
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
  symbolText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  spreadCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#12121a',
    marginHorizontal: 16,
    padding: 12,
    borderRadius: 12,
    marginBottom: 12,
  },
  spreadItem: {
    alignItems: 'center',
  },
  spreadLabel: {
    color: '#666',
    fontSize: 11,
    marginBottom: 4,
  },
  spreadValue: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  content: {
    flex: 1,
    flexDirection: 'row',
    paddingHorizontal: 16,
  },
  domContainer: {
    flex: 2,
    backgroundColor: '#12121a',
    borderRadius: 12,
    marginRight: 8,
    overflow: 'hidden',
  },
  domHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#1a1a2e',
  },
  domHeaderText: {
    color: '#666',
    fontSize: 10,
    fontWeight: '600',
    flex: 1,
    textAlign: 'center',
  },
  domScroll: {
    flex: 1,
  },
  domRow: {
    flexDirection: 'row',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a2e',
  },
  domQuantityContainer: {
    flex: 1,
    position: 'relative',
    justifyContent: 'center',
  },
  domBar: {
    position: 'absolute',
    height: '100%',
    borderRadius: 2,
  },
  domBarBid: {
    right: 0,
  },
  domBarAsk: {
    left: 0,
  },
  domQuantity: {
    color: '#888',
    fontSize: 11,
    paddingHorizontal: 4,
  },
  domPrice: {
    width: 80,
    textAlign: 'center',
    fontSize: 11,
    fontWeight: '600',
  },
  spreadSeparator: {
    backgroundColor: '#1a1a2e',
    paddingVertical: 6,
    alignItems: 'center',
  },
  spreadSeparatorText: {
    color: '#ffa502',
    fontSize: 10,
    fontWeight: '600',
  },
  tapeContainer: {
    flex: 1,
    backgroundColor: '#12121a',
    borderRadius: 12,
    overflow: 'hidden',
  },
  tapeTitle: {
    color: '#666',
    fontSize: 11,
    fontWeight: '600',
    textAlign: 'center',
    paddingVertical: 8,
    backgroundColor: '#1a1a2e',
  },
  tapeScroll: {
    flex: 1,
    padding: 8,
  },
  tradeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 3,
  },
  tradePrice: {
    flex: 1,
    fontSize: 10,
    fontWeight: '600',
  },
  tradeQty: {
    color: '#888',
    fontSize: 10,
    marginRight: 4,
  },
  emptyTape: {
    color: '#444',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 20,
  },
  disconnectedOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(10, 10, 15, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  disconnectedText: {
    color: '#fff',
    fontSize: 16,
    marginTop: 16,
  },
  disconnectedSubtext: {
    color: '#666',
    fontSize: 14,
    marginTop: 8,
  },
});
