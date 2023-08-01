import asyncio
import threading

import hivemind
from async_timeout import timeout

from petals.server.handler import TransformerConnectionHandler

cache_lock = threading.Lock()
info_cache = hivemind.TimedStorage()


async def check_reachability(peer_id, _, node, *, fetch_info=False, connect_timeout=5, expiration=300, use_cache=True):
    with cache_lock:
        if use_cache and peer_id in info_cache:
            return info_cache.get(peer_id).value

    try:
        with timeout(connect_timeout):
            if fetch_info:  # For Petals servers
                stub = TransformerConnectionHandler.get_stub(node.p2p, peer_id)
                response = await stub.rpc_info(hivemind.proto.runtime_pb2.ExpertUID())
                rpc_info = hivemind.MSGPackSerializer.loads(response.serialized_info)
                rpc_info["ok"] = True
            else:  # For DHT-only bootstrap peers
                await node.p2p._client.connect(peer_id, [])
                await node.p2p._client.disconnect(peer_id)
                rpc_info = {"ok": True}
    except Exception as e:
        # Actual connection error
        if not isinstance(e, asyncio.TimeoutError):
            message = str(e) if str(e) else repr(e)
            if message == "protocol not supported":
                # This may be returned when a server is joining, see https://github.com/petals-infra/health.petals.dev/issues/1
                return {"ok": True}
        else:
            message = f"Failed to connect in {connect_timeout:.0f} sec. Firewall may be blocking connections"
        rpc_info = {"ok": False, "error": message}

    with cache_lock:
        info_cache.store(peer_id, rpc_info, hivemind.get_dht_time() + expiration)
    return rpc_info


async def check_reachability_parallel(peer_ids, dht, node, *, fetch_info=False):
    rpc_infos = await asyncio.gather(
        *[check_reachability(peer_id, dht, node, fetch_info=fetch_info) for peer_id in peer_ids]
    )
    return dict(zip(peer_ids, rpc_infos))
