
import socket
import struct
import random
import urllib.parse
from typing import List, Dict, Tuple

class TrackerScraper:
    def __init__(self, timeout=3):
        self.timeout = timeout

    def scrape_udp(self, tracker_url: str, info_hashes: List[str]) -> Dict[str, Tuple[int, int]]:
        """
        Scrape a UDP tracker for seeders/leechers for multiple info_hashes.
        Returns a dict: {info_hash: (seeders, peers)}
        """
        parsed = urllib.parse.urlparse(tracker_url)
        if parsed.scheme != 'udp':
            return {}

        hostname = parsed.hostname
        port = parsed.port
        if not port: return {}

        # Max 74 hashes per scrape request typically
        results = {}
        
        # Split into chunks of 74
        chunks = [info_hashes[i:i + 74] for i in range(0, len(info_hashes), 74)]

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            
            # 1. Connect
            connection_id = self._udp_connect(sock, (hostname, port))
            if not connection_id:
                return {}

            # 2. Scrape chunks
            for chunk in chunks:
                chunk_results = self._udp_scrape_chunk(sock, (hostname, port), connection_id, chunk)
                results.update(chunk_results)
                
            return results
        except Exception as e:
            # print(f"Scrape error {tracker_url}: {e}")
            return {}
        finally:
            if 'sock' in locals():
                sock.close()

    def _udp_connect(self, sock, addr):
        protocol_id = 0x41727101980
        action = 0  # Connect
        trans_id = random.randint(0, 65535)

        req = struct.pack("!QII", protocol_id, action, trans_id)
        try:
            sock.sendto(req, addr)
            resp, _ = sock.recvfrom(16)
            if len(resp) < 16: return None
            
            r_action, r_trans_id, conn_id = struct.unpack("!IIQ", resp)
            if r_trans_id == trans_id and r_action == 0:
                return conn_id
        except:
            return None
        return None

    def _udp_scrape_chunk(self, sock, addr, connection_id, hashes):
        action = 2  # Scrape
        trans_id = random.randint(0, 65535)
        
        # Build request
        req = struct.pack("!QII", connection_id, action, trans_id)
        for h in hashes:
            try:
                req += bytes.fromhex(h)
            except: 
                req += b'\x00' * 20 # Pad invalid hash?

        try:
            sock.sendto(req, addr)
            resp, _ = sock.recvfrom(8 + 12 * len(hashes))
            
            if len(resp) < 8: return {}
            
            r_action, r_trans_id = struct.unpack("!II", resp[:8])
            if r_trans_id != trans_id or r_action != 2:
                return {}
            
            # Parse stats
            results = {}
            for i, h in enumerate(hashes):
                offset = 8 + i * 12
                if offset + 12 > len(resp): break
                
                seeders, completed, leechers = struct.unpack("!III", resp[offset:offset+12])
                results[h] = (seeders, leechers)
                
            return results
        except:
            return {}
