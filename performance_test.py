#!/usr/bin/env python3
"""
WYD Backend Performance Test Suite
Bu test suite sistemin aynı anda kaç işlem kaldırabileceğini test eder.
"""

import asyncio
import aiohttp
import time
import statistics
import json
from concurrent.futures import ThreadPoolExecutor
import psutil
import redis
import motor.motor_asyncio
from kafka import KafkaProducer
import psycopg2
from typing import List, Dict, Any
import uuid

# Test Konfigürasyonu
BASE_URL = "http://localhost:8000"
CONCURRENT_USERS = [10, 50, 100, 500, 1000, 2000, 5000]  # Test edilecek eşzamanlı kullanıcı sayıları
REQUESTS_PER_USER = 10  # Her kullanıcının yapacağı request sayısı

class PerformanceTestSuite:
    def __init__(self):
        self.results = []
        self.system_stats = []
        
    async def setup_test_data(self):
        """Test için gerekli veriyi hazırla"""
        print("🔧 Test verileri hazırlanıyor...")
        
        # Test kullanıcıları oluştur
        self.test_users = []
        for i in range(max(CONCURRENT_USERS)):
            user_data = {
                "username": f"testuser{i}_{uuid.uuid4().hex[:6]}",
                "email": f"test{i}_{uuid.uuid4().hex[:6]}@test.com",
                "password": "123456",
                "name": f"Test{i}",
                "surname": f"User{i}",
                "phone_number": f"123456789{i % 10}",
                "display_name": f"Test User {i}"
            }
            self.test_users.append(user_data)
            
        print(f"✅ {len(self.test_users)} test kullanıcısı hazırlandı")
        
    def get_system_stats(self):
        """Sistem kaynak kullanımını al"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('C:' if psutil.os.name == 'nt' else '/')
        
        return {
            'timestamp': time.time(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_mb': memory.available / 1024 / 1024,
            'disk_percent': disk.percent
        }

    async def single_user_scenario(self, session: aiohttp.ClientSession, user_id: int):
        """Tek kullanıcının yapacağı işlemler senaryosu"""
        user_data = self.test_users[user_id]
        timings = []
        errors = []
        
        try:
            # 1. Kullanıcı kaydı
            start_time = time.time()
            async with session.post(f"{BASE_URL}/api/users/register", json=user_data) as resp:
                if resp.status == 200:
                    user_info = await resp.json()
                    timings.append(('register', time.time() - start_time))
                else:
                    errors.append(('register', resp.status))
                    
            # 2. Giriş yapma (Form data kullan)
            start_time = time.time()
            login_data = {
                "username": user_data["username"], 
                "password": user_data["password"],
                "device_id": f"test_device_{user_id}"
            }
            async with session.post(f"{BASE_URL}/api/users/login", data=login_data) as resp:
                if resp.status == 200:
                    auth_data = await resp.json()
                    token = auth_data.get('access_token')
                    timings.append(('login', time.time() - start_time))
                else:
                    errors.append(('login', resp.status))
                    return timings, errors
                    
            # Authorization header
            headers = {'Authorization': f'Bearer {token}'}
            
            # 3. Profil bilgilerini alma (birkaç kez) - user_id ile
            if 'id' in locals() and user_info and 'id' in user_info:
                user_profile_id = user_info['id']
                for _ in range(2):
                    start_time = time.time()
                    async with session.get(f"{BASE_URL}/api/users/{user_profile_id}", headers=headers) as resp:
                        if resp.status == 200:
                            timings.append(('profile_fetch', time.time() - start_time))
                        else:
                            errors.append(('profile_fetch', resp.status))
                            
                # Friends listesini alma
                start_time = time.time()
                async with session.get(f"{BASE_URL}/api/users/me/friends", headers=headers) as resp:
                    if resp.status == 200:
                        timings.append(('friends_fetch', time.time() - start_time))
                    else:
                        errors.append(('friends_fetch', resp.status))
                        
            # 4. Mesaj gönderme
            for i in range(2):
                start_time = time.time()
                message_data = {
                    "receiver_id": (user_id + 1) % len(self.test_users) + 1,  # Başka bir kullanıcıya
                    "content": f"Test message {i} from user {user_id}",
                    "message_type": "text"
                }
                async with session.post(f"{BASE_URL}/api/messages/send", 
                                      json=message_data, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        timings.append(('send_message', time.time() - start_time))
                    else:
                        errors.append(('send_message', resp.status))
                        
            # 5. Health check
            start_time = time.time()
            async with session.get(f"{BASE_URL}/healthz") as resp:
                if resp.status == 200:
                    timings.append(('health_check', time.time() - start_time))
                else:
                    errors.append(('health_check', resp.status))
                    
        except Exception as e:
            errors.append(('exception', str(e)))
            
        return timings, errors

    async def concurrent_test(self, concurrent_users: int):
        """Eşzamanlı kullanıcı testi"""
        print(f"🔥 {concurrent_users} eşzamanlı kullanıcı testi başlıyor...")
        
        # Sistem durumunu kaydet (test öncesi)
        pre_stats = self.get_system_stats()
        
        connector = aiohttp.TCPConnector(limit=concurrent_users * 2)
        timeout = aiohttp.ClientTimeout(total=30)
        
        start_time = time.time()
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Tüm kullanıcıları paralel olarak çalıştır
            tasks = []
            for user_id in range(concurrent_users):
                task = asyncio.create_task(self.single_user_scenario(session, user_id))
                tasks.append(task)
                
            # Tüm taskları bekle
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Sistem durumunu kaydet (test sonrası)
        post_stats = self.get_system_stats()
        
        # Sonuçları analiz et
        successful_users = 0
        total_requests = 0
        total_errors = 0
        all_timings = []
        
        for result in results:
            if isinstance(result, Exception):
                total_errors += 1
                continue
                
            timings, errors = result
            if timings:  # En az bir işlem başarılı
                successful_users += 1
                all_timings.extend([t[1] for t in timings])
                total_requests += len(timings)
                total_errors += len(errors)
                
        # İstatistikleri hesapla
        if all_timings:
            avg_response_time = statistics.mean(all_timings)
            median_response_time = statistics.median(all_timings)
            p95_response_time = sorted(all_timings)[int(len(all_timings) * 0.95)]
            p99_response_time = sorted(all_timings)[int(len(all_timings) * 0.99)]
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0
            
        requests_per_second = total_requests / total_duration if total_duration > 0 else 0
        success_rate = (successful_users / concurrent_users) * 100
        
        test_result = {
            'concurrent_users': concurrent_users,
            'duration_seconds': total_duration,
            'successful_users': successful_users,
            'total_requests': total_requests,
            'total_errors': total_errors,
            'requests_per_second': requests_per_second,
            'success_rate_percent': success_rate,
            'avg_response_time_ms': avg_response_time * 1000,
            'median_response_time_ms': median_response_time * 1000,
            'p95_response_time_ms': p95_response_time * 1000,
            'p99_response_time_ms': p99_response_time * 1000,
            'system_stats': {
                'pre_test': pre_stats,
                'post_test': post_stats,
                'cpu_increase': post_stats['cpu_percent'] - pre_stats['cpu_percent'],
                'memory_increase': post_stats['memory_percent'] - pre_stats['memory_percent']
            }
        }
        
        self.results.append(test_result)
        
        # Sonuçları yazdır
        print(f"✅ {concurrent_users} kullanıcı testi tamamlandı:")
        print(f"   📊 Başarı Oranı: {success_rate:.1f}%")
        print(f"   ⚡ RPS: {requests_per_second:.1f}")
        print(f"   ⏱️  Ortalama Yanıt: {avg_response_time * 1000:.1f}ms")
        print(f"   🎯 P95 Yanıt: {p95_response_time * 1000:.1f}ms")
        print(f"   🖥️  CPU Artışı: {post_stats['cpu_percent'] - pre_stats['cpu_percent']:.1f}%")
        print(f"   💾 Bellek Artışı: {post_stats['memory_percent'] - pre_stats['memory_percent']:.1f}%")
        print()
        
        return test_result

    async def database_stress_test(self):
        """Veritabanı stres testi"""
        print("🔥 Veritabanı stres testi başlıyor...")
        
        # Redis stress test
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            
            start_time = time.time()
            operations = 10000
            
            # Pipeline ile toplu işlem
            pipe = r.pipeline()
            for i in range(operations):
                pipe.set(f"stress_test_key_{i}", f"value_{i}")
                pipe.get(f"stress_test_key_{i}")
            pipe.execute()
            
            redis_duration = time.time() - start_time
            redis_ops_per_sec = (operations * 2) / redis_duration  # set + get
            
            print(f"✅ Redis: {redis_ops_per_sec:.0f} ops/sec")
            
        except Exception as e:
            print(f"❌ Redis hatası: {e}")
            
        # MongoDB stress test  
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
            db = client.test_db
            collection = db.stress_test
            
            start_time = time.time()
            operations = 5000
            
            # Toplu insert
            documents = [{"test_id": i, "data": f"test_data_{i}"} for i in range(operations)]
            await collection.insert_many(documents)
            
            # Toplu query
            cursor = collection.find({"test_id": {"$lt": operations}})
            docs = await cursor.to_list(length=operations)
            
            mongo_duration = time.time() - start_time
            mongo_ops_per_sec = (operations * 2) / mongo_duration  # insert + find
            
            print(f"✅ MongoDB: {mongo_ops_per_sec:.0f} ops/sec")
            
            # Temizlik
            await collection.drop()
            
        except Exception as e:
            print(f"❌ MongoDB hatası: {e}")

    def generate_report(self):
        """Detaylı rapor oluştur"""
        print("\n" + "="*80)
        print("🏆 PERFORMANS TESTİ RAPORU")
        print("="*80)
        
        print(f"📅 Test Tarihi: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🖥️  Sistem: {psutil.os.name} - CPU: {psutil.cpu_count()} cores")
        print(f"💾 RAM: {psutil.virtual_memory().total / 1024**3:.1f} GB")
        print()
        
        if not self.results:
            print("❌ Test sonucu bulunamadı!")
            return
            
        # En iyi performans bulma
        best_rps = max(self.results, key=lambda x: x['requests_per_second'])
        best_success = max(self.results, key=lambda x: x['success_rate_percent'])
        
        print("🎯 ÖNE ÇIKAN SONUÇLAR:")
        print(f"   🚀 Maksimum RPS: {best_rps['requests_per_second']:.1f} ({best_rps['concurrent_users']} kullanıcı)")
        print(f"   ✅ En İyi Başarı: %{best_success['success_rate_percent']:.1f} ({best_success['concurrent_users']} kullanıcı)")
        print()
        
        print("📊 DETAYLI SONUÇLAR:")
        print("-" * 80)
        print(f"{'Kullanıcı':<10} {'Başarı %':<10} {'RPS':<12} {'Ort.Yanıt':<12} {'P95':<12} {'CPU+':<8} {'RAM+':<8}")
        print("-" * 80)
        
        for result in self.results:
            print(f"{result['concurrent_users']:<10} "
                  f"{result['success_rate_percent']:<9.1f}% "
                  f"{result['requests_per_second']:<11.1f} "
                  f"{result['avg_response_time_ms']:<11.0f}ms "
                  f"{result['p95_response_time_ms']:<11.0f}ms "
                  f"{result['system_stats']['cpu_increase']:<7.1f}% "
                  f"{result['system_stats']['memory_increase']:<7.1f}%")
        
        # Sonuçları JSON olarak kaydet
        with open('performance_test_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.time(),
                'system_info': {
                    'os': psutil.os.name,
                    'cpu_cores': psutil.cpu_count(),
                    'total_memory_gb': psutil.virtual_memory().total / 1024**3
                },
                'test_results': self.results
            }, f, indent=2, ensure_ascii=False)
            
        print("\n💾 Detaylı sonuçlar 'performance_test_results.json' dosyasına kaydedildi")
        
        # Öneriler
        print("\n🎯 ÖNERİLER:")
        
        failing_tests = [r for r in self.results if r['success_rate_percent'] < 95]
        if failing_tests:
            threshold = min([r['concurrent_users'] for r in failing_tests])
            print(f"   ⚠️  {threshold} kullanıcıdan sonra başarı oranı düşüyor")
            print(f"   💡 Güvenli kapasite: ~{threshold - 100} eşzamanlı kullanıcı")
        else:
            max_tested = max([r['concurrent_users'] for r in self.results])
            print(f"   🚀 {max_tested} kullanıcıya kadar stabil performans!")
            print(f"   💡 Daha yüksek yük testleri yapılabilir")
            
        slow_tests = [r for r in self.results if r['p95_response_time_ms'] > 1000]
        if slow_tests:
            print(f"   🐌 Yanıt süreleri {min([r['concurrent_users'] for r in slow_tests])} kullanıcıdan sonra yavaşlıyor")
            print(f"   💡 Cache optimizasyonu ve database tuning önerilir")

async def main():
    """Ana test fonksiyonu"""
    print("🚀 WYD Backend Performans Testi Başlıyor!")
    print("=" * 50)
    
    test_suite = PerformanceTestSuite()
    
    try:
        # Test verilerini hazırla
        await test_suite.setup_test_data()
        
        # Veritabanı stres testi
        await test_suite.database_stress_test()
        print()
        
        # Farklı concurrent user sayıları ile test
        for concurrent_users in CONCURRENT_USERS:
            try:
                await test_suite.concurrent_test(concurrent_users)
                
                # Testler arası bekleme (sistem dinlensin)
                if concurrent_users < max(CONCURRENT_USERS):
                    print(f"⏳ 5 saniye bekleme... (sistem dinlenmesi)")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                print(f"❌ {concurrent_users} kullanıcı testi hatası: {e}")
                break
        
        # Rapor oluştur
        test_suite.generate_report()
        
    except KeyboardInterrupt:
        print("\n⚠️ Test kullanıcı tarafından durduruldu")
        test_suite.generate_report()
    except Exception as e:
        print(f"\n❌ Test hatası: {e}")

if __name__ == "__main__":
    # Windows için event loop politikası
    if psutil.os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
