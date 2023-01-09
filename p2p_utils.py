import asyncio
import threading

import hivemind
from async_timeout import timeout

cache_lock = threading.Lock()
reachable_cache = hivemind.TimedStorage()


async def check_reachability(peer_id, _, node, *, connect_timeout=5, expiration=600, use_cache=True):
    if use_cache and peer_id in reachable_cache:
        with cache_lock:
            return reachable_cache.get(peer_id).value

    try:
        with timeout(connect_timeout):
            await node.p2p._client.connect(peer_id, [])
            await node.p2p._client.disconnect(peer_id)

        with cache_lock:
            reachable_cache.store(peer_id, None, hivemind.get_dht_time() + expiration)
        return None
    except Exception as e:
        if isinstance(e, asyncio.TimeoutError):
            return f"Failed to connect in {connect_timeout:.0f} sec. Firewall may be blocking connections"
        message = str(e)
        message = message if message else repr(e)

        with cache_lock:
            reachable_cache.store(peer_id, message, hivemind.get_dht_time() + expiration)
        return message


async def check_reachability_parallel(peer_ids, dht, node):
    errors = await asyncio.gather(*[check_reachability(peer_id, dht, node) for peer_id in peer_ids])
    return {peer_id: err for peer_id, err in zip(peer_ids, errors) if err is not None}
