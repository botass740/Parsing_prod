# test_price_calc.py

price_history = 927.6  # Из price-history.json (последняя цена)

print("="*50)
print("ПОДБОР КОЭФФИЦИЕНТОВ ДЛЯ WB")
print("="*50)

print(f"\nЦена из price-history.json: {price_history} ₽")
print(f"Цена на сайте (картой):     1 105 ₽")
print(f"Цена на сайте (кошелёк):    1 082 ₽")
print(f"Старая цена на сайте:       1 650 ₽")

print("\n" + "="*50)
print("РАСЧЁТ MAX_SPP")
print("="*50)

# Находим MAX_SPP
# price_history = price_site * (1 - MAX_SPP)
# MAX_SPP = 1 - (price_history / price_site)
real_spp = 1 - (price_history / 1105)
print(f"\nФормула: MAX_SPP = 1 - ({price_history} / 1105)")
print(f"MAX_SPP = {real_spp:.4f} ({real_spp*100:.2f}%)")

# Проверка
price_site_calc = price_history / (1 - real_spp)
print(f"\nПроверка: {price_history} / (1 - {real_spp:.4f}) = {price_site_calc:.0f} ₽")

print("\n" + "="*50)
print("РАСЧЁТ OLD_PRICE_MULT")
print("="*50)

# Находим множитель старой цены
# old_price = price_site * OLD_PRICE_MULT
# OLD_PRICE_MULT = old_price / price_site
old_mult = 1650 / 1105
print(f"\nФормула: OLD_PRICE_MULT = 1650 / 1105")
print(f"OLD_PRICE_MULT = {old_mult:.4f}")

# Проверка
old_price_calc = 1105 * old_mult
print(f"\nПроверка: 1105 * {old_mult:.4f} = {old_price_calc:.0f} ₽")

print("\n" + "="*50)
print("ИТОГОВЫЕ КОНСТАНТЫ")
print("="*50)

print(f"\nMAX_SPP = {real_spp:.2f}  # (~{real_spp*100:.0f}%)")
print(f"OLD_PRICE_MULT = {old_mult:.2f}")

print("\n" + "="*50)
print("ФИНАЛЬНАЯ ПРОВЕРКА")
print("="*50)

# Применяем формулы
MAX_SPP = round(real_spp, 2)
OLD_PRICE_MULT = round(old_mult, 2)

price_site = price_history / (1 - MAX_SPP)
price_wallet = price_site * 0.98
old_price = price_site * OLD_PRICE_MULT

print(f"\nИсходная цена (history): {price_history} ₽")
print(f"Цена картой:             {price_site:.0f} ₽  (ожидали 1105)")
print(f"Цена кошельком:          {price_wallet:.0f} ₽  (ожидали 1082)")
print(f"Старая цена:             {old_price:.0f} ₽  (ожидали 1650)")

print("\n" + "="*50)