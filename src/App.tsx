import { useState, useEffect, useCallback, useRef } from 'react';
import { 
  ShieldCheck, 
  RefreshCw, 
  Zap, 
  Activity,
  Terminal,
  Cpu,
  Radio,
  Lock,
  CheckCircle,
  XCircle,
  RotateCcw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import './App.css';

// ============================================================================
// TYPES
// ============================================================================

interface Device {
  device_id: string;
  status: 'healthy' | 'compromised' | 'quarantine' | 'offline';
  firmware_version: string;
  last_attestation: string | null;
  uptime_seconds: number;
  pcrs: Record<number, string>;
}

interface LogEntry {
  time: string;
  type: string;
  result: 'PASS' | 'FAIL';
  device_id: string;
  latency_ms?: number;
}

interface TerminalLine {
  time: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

interface PCRMatch {
  [key: number]: boolean;
}

// ============================================================================
// MAIN APP
// ============================================================================

function App() {
  // Connection state
  const [wsConnected, setWsConnected] = useState(false);
  const [hardwareAvailable, setHardwareAvailable] = useState(false);
  
  // Device state
  const [device, setDevice] = useState<Device>({
    device_id: 'FL-2847-AF',
    status: 'healthy',
    firmware_version: 'v2.1.0',
    last_attestation: new Date().toISOString(),
    uptime_seconds: 4060800,
    pcrs: {
      0: '0x7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b',
      1: '0xa1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2',
      2: '0xd4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5',
      3: '0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b'
    }
  });
  
  // Golden PCRs (baseline)
  const [goldenPCRs] = useState<Record<number, string>>({
    0: '0x7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b',
    1: '0xa1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2',
    2: '0xd4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5',
    3: '0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b'
  });
  
  // Logs and terminal
  const [logs, setLogs] = useState<LogEntry[]>([
    { time: '14:32:01', type: 'Scheduled', result: 'PASS', device_id: 'FL-2847-AF', latency_ms: 1.2 },
    { time: '14:15:33', type: 'Manual', result: 'PASS', device_id: 'FL-2847-AF', latency_ms: 0.9 },
    { time: '13:45:00', type: 'Scheduled', result: 'PASS', device_id: 'FL-2847-AF', latency_ms: 1.1 },
  ]);
  const [terminalLines, setTerminalLines] = useState<TerminalLine[]>([
    { time: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'System initialized', type: 'info' },
    { time: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'Connected to device FL-2847-AF', type: 'success' },
    { time: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'Secure channel established', type: 'success' },
  ]);
  
  // Operation states
  const [isAttesting, setIsAttesting] = useState(false);
  const [isRecovering, setIsRecovering] = useState(false);
  const [attestationProgress, setAttestationProgress] = useState(0);
  const [lastLatency, setLastLatency] = useState<number | null>(null);
  const [pcrMatch, setPcrMatch] = useState<PCRMatch>({ 0: true, 1: true, 2: true, 3: true });
  
  // WebSocket ref
  const wsRef = useRef<WebSocket | null>(null);
  const progressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  
  // ============================================================================
  // WEBSOCKET CONNECTION
  // ============================================================================
  
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8000/ws');
      
      ws.onopen = () => {
        console.log('[WEBSOCKET] Connected');
        setWsConnected(true);
        addTerminalLine('WebSocket connected', 'success');
        
        // Request initial data
        ws.send(JSON.stringify({ action: 'get_devices' }));
      };
      
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
      };
      
      ws.onclose = () => {
        console.log('[WEBSOCKET] Disconnected');
        setWsConnected(false);
        addTerminalLine('WebSocket disconnected', 'warning');
        
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      ws.onerror = (error) => {
        console.error('[WEBSOCKET] Error:', error);
        addTerminalLine('WebSocket error', 'error');
      };
      
      wsRef.current = ws;
    };
    
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);
  
  interface WSMessage {
    type: string;
    hardware_available?: boolean;
    data?: Device[];
    result?: string;
    reason?: string;
    pcr_match?: PCRMatch;
    latency_ms?: number;
    device_id?: string;
    pcr_changed?: number;
    status?: string;
    nonce?: string;
  }

  const handleWebSocketMessage = (message: WSMessage) => {
    switch (message.type) {
      case 'connected':
        setHardwareAvailable(message.hardware_available ?? false);
        break;
        
      case 'devices':
        if (message.data && message.data.length > 0) {
          setDevice(message.data[0]);
        }
        break;
        
      case 'attestation_complete':
        if (message.result && message.latency_ms !== undefined) {
          handleAttestationComplete(message as { result: string; reason?: string; pcr_match?: PCRMatch; latency_ms: number });
        }
        break;
        
      case 'attack_detected':
        if (message.device_id && message.pcr_changed !== undefined) {
          handleAttackDetected(message as { device_id: string; pcr_changed: number });
        }
        break;
        
      case 'device_recovered':
        if (message.device_id && message.status) {
          handleDeviceRecovered(message as { device_id: string; status: string });
        }
        break;
        
      case 'challenge_created':
        if (message.nonce) {
          addTerminalLine(`Challenge created: ${message.nonce.substring(0, 16)}...`, 'info');
        }
        break;
    }
  };
  
  // ============================================================================
  // TERMINAL
  // ============================================================================
  
  const addTerminalLine = useCallback((message: string, type: TerminalLine['type'] = 'info') => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    setTerminalLines(prev => [...prev, { time, message, type }].slice(-50));
  }, []);
  
  // ============================================================================
  // ATTESTATION
  // ============================================================================
  
  const triggerAttestation = async () => {
    if (isAttesting || !wsRef.current) return;
    
    setIsAttesting(true);
    setAttestationProgress(0);
    addTerminalLine('Starting attestation...', 'info');
    
    // Progress animation
    progressIntervalRef.current = setInterval(() => {
      setAttestationProgress(prev => {
        if (prev >= 90) return prev;
        return prev + 10;
      });
    }, 100);
    
    // Send attestation request
    wsRef.current.send(JSON.stringify({
      action: 'trigger_attestation',
      device_id: device.device_id
    }));
  };
  
  const handleAttestationComplete = (msg: { result: string; reason?: string; pcr_match?: PCRMatch; latency_ms: number }) => {
    setIsAttesting(false);
    setAttestationProgress(100);
    
    // Clear progress interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    
    const { result, reason, pcr_match, latency_ms } = msg;
    
    setLastLatency(latency_ms);
    
    // Update device status
    setDevice(prev => ({
      ...prev,
      status: result === 'PASS' ? 'healthy' : 'compromised',
      last_attestation: new Date().toISOString()
    }));
    
    // Add log
    const newLog: LogEntry = {
      time: new Date().toLocaleTimeString('en-US', { hour12: false }),
      type: 'Manual',
      result: (result === 'PASS' ? 'PASS' : 'FAIL') as 'PASS' | 'FAIL',
      device_id: device.device_id,
      latency_ms: latency_ms
    };
    setLogs(prev => [newLog, ...prev].slice(20));
    
    // Terminal output
    if (result === 'PASS') {
      addTerminalLine(`✓ Attestation PASSED (${latency_ms}ms)`, 'success');
      addTerminalLine('All PCRs match golden values', 'success');
    } else {
      addTerminalLine(`✗ Attestation FAILED: ${reason}`, 'error');
      if (pcr_match) {
        Object.entries(pcr_match).forEach(([idx, match]) => {
          if (!match) {
            addTerminalLine(`✗ PCR[${idx}] MISMATCH!`, 'error');
          }
        });
      }
    }
    
    setTimeout(() => setAttestationProgress(0), 500);
  };
  
  // ============================================================================
  // ATTACK SIMULATION
  // ============================================================================
  
  const simulateAttack = () => {
    if (!wsRef.current) return;
    
    addTerminalLine('⚠️ ATTACK SIMULATION STARTED', 'warning');
    addTerminalLine('Attacker connecting SWD debugger...', 'warning');
    
    setTimeout(() => {
      addTerminalLine('Reading original firmware...', 'warning');
    }, 500);
    
    setTimeout(() => {
      addTerminalLine('Injecting malicious payload...', 'warning');
    }, 1000);
    
    setTimeout(() => {
      addTerminalLine('Flashing modified firmware...', 'warning');
    }, 1500);
    
    setTimeout(() => {
      wsRef.current?.send(JSON.stringify({
        action: 'simulate_attack',
        device_id: device.device_id
      }));
      
      // Modify PCR[1] locally for immediate feedback
      setDevice(prev => ({
        ...prev,
        status: 'compromised',
        pcrs: {
          ...prev.pcrs,
          1: '0xe5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6'
        }
      }));
      
      setPcrMatch(prev => ({ ...prev, 1: false }));
      addTerminalLine('✗ Device compromised! PCR[1] modified', 'error');
    }, 2000);
  };
  
  const handleAttackDetected = (msg: { device_id: string; pcr_changed: number }) => {
    addTerminalLine(`Attack detected on device ${msg.device_id}`, 'error');
    addTerminalLine(`PCR[${msg.pcr_changed}] changed`, 'error');
  };
  
  // ============================================================================
  // RECOVERY
  // ============================================================================
  
  const triggerRecovery = () => {
    if (isRecovering || !wsRef.current) return;
    
    setIsRecovering(true);
    addTerminalLine('🛡️ Recovery initiated...', 'info');
    addTerminalLine('Verifying golden image signature...', 'info');
    
    wsRef.current.send(JSON.stringify({
      action: 'trigger_recovery',
      device_id: device.device_id
    }));
  };
  
  const handleDeviceRecovered = (_msg: { device_id: string; status: string }) => {
    setIsRecovering(false);
    
    // Restore golden PCRs
    setDevice(prev => ({
      ...prev,
      status: 'healthy',
      firmware_version: 'v2.1.0-factory',
      pcrs: { ...goldenPCRs }
    }));
    
    // Reset PCR match state
    setPcrMatch({ 0: true, 1: true, 2: true, 3: true });
    
    addTerminalLine('✓ Golden image verified', 'success');
    addTerminalLine('✓ Flash write complete', 'success');
    addTerminalLine('✓ Device restored to trusted state', 'success');
  };
  
  // ============================================================================
  // HELPERS
  // ============================================================================
  
  const getStatusBadge = (status: Device['status']) => {
    const styles = {
      healthy: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
      compromised: 'bg-red-500/15 text-red-400 border-red-500/30 animate-pulse',
      quarantine: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
      offline: 'bg-slate-500/15 text-slate-400 border-slate-500/30'
    };
    
    const labels = {
      healthy: '🟢 HEALTHY',
      compromised: '🔴 COMPROMISED',
      quarantine: '⚠️ QUARANTINE',
      offline: '⚫ OFFLINE'
    };
    
    return (
      <Badge className={cn('font-semibold border', styles[status])}>
        {labels[status]}
      </Badge>
    );
  };
  
  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return `${days} days ${hours}h`;
  };
  
  const formatPCR = (pcr: string) => {
    if (pcr.length <= 20) return pcr;
    return `${pcr.substring(0, 10)}...${pcr.substring(pcr.length - 10)}`;
  };
  
  // ============================================================================
  // RENDER
  // ============================================================================
  
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white font-sans">
      {/* Background Grid */}
      <div 
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0, 212, 170, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 212, 170, 0.03) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }}
      />
      
      <div className="relative z-10 max-w-[1400px] mx-auto p-6">
        {/* Header */}
        <header className="flex items-center justify-between mb-8 pb-6 border-b border-slate-800">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-xl flex items-center justify-center text-2xl shadow-lg shadow-emerald-500/20">
              🔒
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">FIRM-LOCK</h1>
              <p className="text-xs text-slate-400 uppercase tracking-widest">Attestation Dashboard</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3 px-4 py-2 bg-slate-900/80 rounded-full border border-slate-700">
            <div className={cn(
              'w-2.5 h-2.5 rounded-full animate-pulse',
              wsConnected ? 'bg-emerald-400' : 'bg-red-400'
            )} />
            <span className="text-sm text-slate-300">
              {wsConnected ? 'Device Connected' : 'Disconnected'}
            </span>
            {hardwareAvailable && (
              <Badge variant="outline" className="text-xs border-emerald-500/30 text-emerald-400">
                Hardware
              </Badge>
            )}
          </div>
        </header>
        
        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Device Status & PCRs */}
          <div className="lg:col-span-2 space-y-6">
            {/* Device Status Card */}
            <Card className="bg-slate-900/80 border-slate-700">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                  Device Status
                </CardTitle>
                {getStatusBadge(device.status)}
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-800/50 rounded-lg p-4">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Device ID</p>
                    <p className="font-mono text-sm text-white">{device.device_id}</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-4">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Firmware</p>
                    <p className="font-mono text-sm text-white">{device.firmware_version}</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-4">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Last Attestation</p>
                    <p className="font-mono text-sm text-white">
                      {device.last_attestation 
                        ? new Date(device.last_attestation).toLocaleTimeString('en-US', { hour12: false })
                        : 'Never'
                      }
                    </p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-4">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Uptime</p>
                    <p className="font-mono text-sm text-white">{formatUptime(device.uptime_seconds)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* PCR Values Card */}
            <Card className="bg-slate-900/80 border-slate-700">
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                  PCR Values (Platform Configuration Registers)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[0, 1, 2, 3].map((idx) => {
                    const pcr = device.pcrs[idx];
                    const matches = pcrMatch[idx] ?? (pcr === goldenPCRs[idx]);
                    const labels = ['Bootloader', 'Application', 'Configuration', 'Identity'];
                    
                    return (
                      <div 
                        key={idx} 
                        className={cn(
                          'flex items-center gap-4 p-4 rounded-lg border transition-all',
                          matches 
                            ? 'bg-slate-800/30 border-slate-700' 
                            : 'bg-red-500/10 border-red-500/30'
                        )}
                      >
                        <div className={cn(
                          'w-10 h-10 rounded-lg flex items-center justify-center font-mono font-bold text-sm',
                          matches 
                            ? 'bg-slate-800 text-emerald-400' 
                            : 'bg-red-500/20 text-red-400'
                        )}>
                          {idx}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-slate-400 mb-1">{labels[idx]} Measurement</p>
                          <p className={cn(
                            'font-mono text-sm truncate',
                            matches ? 'text-white' : 'text-red-300'
                          )}>
                            {formatPCR(pcr)}
                          </p>
                        </div>
                        <div className={cn(
                          'w-8 h-8 rounded-full flex items-center justify-center',
                          matches 
                            ? 'bg-emerald-500/15 text-emerald-400' 
                            : 'bg-red-500/15 text-red-400 animate-pulse'
                        )}>
                          {matches ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
            
            {/* Terminal */}
            <Card className="bg-slate-900/80 border-slate-700">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <Terminal className="w-4 h-4" />
                  Live Terminal
                </CardTitle>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => setTerminalLines([])}
                  className="text-slate-400 hover:text-white"
                >
                  Clear
                </Button>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[200px] bg-black/50 rounded-lg border border-slate-800 p-4 font-mono text-sm">
                  {terminalLines.map((line, idx) => (
                    <div key={idx} className="flex gap-3 mb-1">
                      <span className="text-slate-500">[{line.time}]</span>
                      <span className={cn(
                        line.type === 'success' && 'text-emerald-400',
                        line.type === 'error' && 'text-red-400',
                        line.type === 'warning' && 'text-amber-400',
                        line.type === 'info' && 'text-blue-400'
                      )}>
                        {line.message}
                      </span>
                    </div>
                  ))}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
          
          {/* Right Column - Actions & Logs */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <Card className="bg-slate-900/80 border-slate-700">
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button 
                  className="w-full bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-black font-semibold"
                  onClick={triggerAttestation}
                  disabled={isAttesting || !wsConnected}
                >
                  {isAttesting ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Activity className="w-4 h-4 mr-2" />
                  )}
                  {isAttesting ? 'Attesting...' : 'Trigger Attestation'}
                </Button>
                
                {isAttesting && (
                  <Progress value={attestationProgress} className="h-2" />
                )}
                
                <Button 
                  variant="outline"
                  className="w-full border-slate-600 hover:border-emerald-500 hover:text-emerald-400"
                  onClick={() => addTerminalLine('Viewing PCR history...', 'info')}
                >
                  <Activity className="w-4 h-4 mr-2" />
                  View PCR History
                </Button>
                
                <Separator className="bg-slate-700" />
                
                <Button 
                  variant="outline"
                  className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                  onClick={simulateAttack}
                  disabled={!wsConnected}
                >
                  <Zap className="w-4 h-4 mr-2" />
                  Simulate Attack
                </Button>
                
                <Button 
                  variant="outline"
                  className="w-full border-amber-500/30 text-amber-400 hover:bg-amber-500/10 hover:text-amber-300"
                  onClick={triggerRecovery}
                  disabled={isRecovering || device.status === 'healthy' || !wsConnected}
                >
                  {isRecovering ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <RotateCcw className="w-4 h-4 mr-2" />
                  )}
                  {isRecovering ? 'Recovering...' : 'Trigger Recovery'}
                </Button>
                
                <Button 
                  variant="outline"
                  className="w-full border-slate-600 hover:border-emerald-500"
                  onClick={() => {
                    const logsData = logs.map(l => `[${l.time}] ${l.type}: ${l.result}`).join('\n');
                    const blob = new Blob([logsData], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'firmlock-logs.txt';
                    a.click();
                    addTerminalLine('Logs exported', 'success');
                  }}
                >
                  <Lock className="w-4 h-4 mr-2" />
                  Export Logs
                </Button>
              </CardContent>
            </Card>
            
            {/* Attestation Log */}
            <Card className="bg-slate-900/80 border-slate-700">
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                  Attestation Log
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[250px]">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left border-b border-slate-700">
                        <th className="pb-2 text-xs text-slate-500 uppercase">Time</th>
                        <th className="pb-2 text-xs text-slate-500 uppercase">Type</th>
                        <th className="pb-2 text-xs text-slate-500 uppercase">Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {logs.map((log, idx) => (
                        <tr key={idx} className="border-b border-slate-800/50 last:border-0">
                          <td className="py-2 text-sm text-slate-300">{log.time}</td>
                          <td className="py-2 text-sm text-slate-400">{log.type}</td>
                          <td className="py-2">
                            <Badge className={cn(
                              'text-xs',
                              log.result === 'PASS' 
                                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                                : 'bg-red-500/15 text-red-400 border-red-500/30'
                            )}>
                              {log.result === 'PASS' ? '✅' : '❌'} {log.result}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </div>
        
        {/* Metrics Footer */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          {[
            { label: 'Boot Time', value: '580ms', icon: Cpu },
            { label: 'Attestation Latency', value: lastLatency ? `${lastLatency}ms` : '1.2s', icon: Activity },
            { label: 'Sleep Power', value: '9µA', icon: Radio },
            { label: 'Detection Rate', value: '100%', icon: ShieldCheck },
          ].map((metric, idx) => (
            <Card key={idx} className="bg-slate-900/80 border-slate-700">
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-emerald-400 font-mono">{metric.value}</p>
                <p className="text-xs text-slate-500 uppercase tracking-wider mt-1">{metric.label}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
