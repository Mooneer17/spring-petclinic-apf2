# Re-test y regresion antes/despues (MySQL 8.0.46, 2026-11-26)
Original: rama main (8ecb2ec), puerto 8081, BD petclinic_base.
Corregida: rama correcciones-apf3 (b2e4b91), puerto 8082, BD petclinic_fix.

## Suites completas
| Suite | Original | Corregida |
|---|---|---|
| Funcionales HTTP (31) | 31 aprobados | 31 aprobados |
| Seguridad HTTP (13) | 7 aprobados, 5 fallidos, 1 observacion | 11 aprobados, 1 fallido (S11), 1 observacion |
| JUnit en MySQL (14) | 7 fallos (E01 y 6 de seguridad) | 0 fallos |

## E01 duplicado concurrente (10 propietarios x 4 POST)
| Corrida | Original | Corregida |
|---|---|---|
| 1 | 302=14, 500=26, 4 huerfanas | 302=10, 200 con error de nombre=30, 0 huerfanas |
| 2 | 302=14, 500=26, 4 huerfanas | 302=10, 200 con error=30, 0 huerfanas |
| 3 | 302=16, 500=24, 6 huerfanas | 302=10, 200 con error=30, 0 huerfanas |
