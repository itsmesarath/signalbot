import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Platform } from 'react-native';

// Tab bar icon component to avoid inline function issues
const TabBarIcon = ({ name, color, size }: { name: keyof typeof Ionicons.glyphMap; color: string; size: number }) => (
  <Ionicons name={name} size={size} color={color} />
);

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarActiveTintColor: '#00d4aa',
        tabBarInactiveTintColor: '#666',
        tabBarLabelStyle: styles.tabLabel,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Dashboard',
          tabBarIcon: ({ color, size }) => <TabBarIcon name="stats-chart" color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="signals"
        options={{
          title: 'Signals',
          tabBarIcon: ({ color, size }) => <TabBarIcon name="pulse" color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="orderbook"
        options={{
          title: 'DOM',
          tabBarIcon: ({ color, size }) => <TabBarIcon name="list" color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color, size }) => <TabBarIcon name="settings" color={color} size={size} />,
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: '#12121a',
    borderTopColor: '#1a1a2e',
    borderTopWidth: 1,
    height: Platform.OS === 'ios' ? 88 : 64,
    paddingBottom: Platform.OS === 'ios' ? 28 : 8,
    paddingTop: 8,
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: '600',
  },
});
