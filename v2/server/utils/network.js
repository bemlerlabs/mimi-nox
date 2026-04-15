/**
 * ◑ MiMiNox v2 — Network Utilities
 * server/utils/network.js
 */

import dns from 'node:dns/promises';

/**
 * Checks if the system has internet access.
 * Tries to resolve a well-known DNS name with a short timeout.
 * 
 * @param {number} timeoutMs - Timeout in milliseconds
 * @returns {Promise<boolean>}
 */
export async function isInternetAvailable(timeoutMs = 2000) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    // Try to lookup a reliable public DNS
    // Note: We use lookupService or similar that might be affected by local cache, 
    // but usually if you're air-gapped, this fails.
    await dns.lookup('1.1.1.1', { signal: controller.signal });
    
    clearTimeout(timer);
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Gets the local IP address of the machine.
 * Port of utils/network.py get_local_ip() logic.
 */
import { networkInterfaces } from 'node:os';

export function getLocalIp() {
  const nets = networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      // Skip internal (127.0.0.1) and non-IPv4 addresses
      if (net.family === 'IPv4' && !net.internal) {
        return net.address;
      }
    }
  }
  return '127.0.0.1';
}
