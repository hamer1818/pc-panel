"""Windows karşılıkları: medya (GSMTC), ses (Core Audio), bildirimler, uygulamalar, sensörler, oturum.

Linux modülleriyle (media.py, audio.py, notify.py, apps.py) aynı arayüzü sunar; seçim `pc_panel.backend`'de.

COM: winrt ve comtypes aynı süreçte çalışır. İkisi de "çok iş parçacıklı daire" (MTA) ile başlatılır; aksi hâlde
ikincisi RPC_E_CHANGED_MODE ile düşer. comtypes ilk içe aktarılışta `sys.coinit_flags`'e bakar, bu yüzden bu
paket her şeyden önce yüklenir. MTA'nın bir yararı da `asyncio.to_thread` iş parçacıklarının COM'u ayrıca
başlatmadan kullanabilmesi.
"""

import sys

sys.coinit_flags = 0  # COINIT_MULTITHREADED

import comtypes  # noqa: E402,F401  (COM'u MTA ile başlatır; winrt'den önce)
