# M1 VWAP — Real-data test (29 May 2026, GOLD)

## Test config
- Symbol: GOLD (FxPro)
- TF: M1
- Window: 60 bars (1 hour)
- VWAP: rolling from start of window (not session-open)
- Candidate conditions: price < VWAP - 3pts, volume > avg(10), price > VWAP - 10pts, last candle green

## Raw data (last 15 of 60 bars)
```
Свеча | Цена  | VWAP   | Откл    | Объём | Ср.об | Сигнал
 1    | 4571.51 | 4566.79 | +472pts |  566 | 578 | -
 2    | 4570.76 | 4566.88 | +388pts |  573 | 576 | -
 3    | 4570.00 | 4566.95 | +305pts |  562 | 574 | -
 4    | 4569.59 | 4567.01 | +258pts |  541 | 572 | -
 5    | 4567.37 | 4567.04 | +33pts  |  566 | 569 | -
 6    | 4565.48 | 4567.03 | -155pts |  561 | 568 | -
 7    | 4565.47 | 4567.00 | -153pts |  569 | 566 | -
 8    | 4566.16 | 4566.97 | -81pts  |  546 | 564 | -
 9    | 4564.85 | 4566.95 | -210pts |  564 | 562 | -
10    | 4562.09 | 4566.88 | -479pts |  578 | 561 | -
11    | 4562.53 | 4566.80 | -427pts |  560 | 563 | -
12    | 4562.78 | 4566.72 | -394pts |  560 | 562 | -
13    | 4564.65 | 4566.66 | -201pts |  576 | 561 | -
14    | 4565.35 | 4566.63 | -129pts |  553 | 563 | -
15    | 4565.21 | 4566.63 | -142pts |  157 | 564 | -
```

## Result: 0 signals in 60 minutes

## Root cause analysis
The condition "price > VWAP - 10pts" (= 4565.63) was violated on bar #10 (4562.09). Every subsequent bar was also below this threshold. The market moved 9pts in 10 minutes (4571→4562), so the ±10pts guardrail was hit immediately and never recovered.

## Fix applied
Guardrail expanded from ±10pts to ±20pts. Added 2-candle confirmation as primary entry gate. During a 7pt drop in 10 minutes, ANY static guardrail will be hit — the 2-candle confirmation prevents catching the falling knife by ensuring at least 2 green candles before entry.

## Practical guideline for GOLD M1
- GOLD intraday M1 range = typically 5-15pts per hour
- Static VWAP ± guardrail will fail during directional phases
- Best combo: VWAP trend direction + volume spike + candle confirmation
- Guardrail at ±20pts is wide enough for most phases; tighten to ±15pts during calm sessions (ATR < 6)
