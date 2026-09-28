# V7 technical references

Retrieved/reviewed 2026-09-28. These are method references, not proof of model-to-hardware fidelity or electrical product certification. The nominal specification is the user's updated 240 Vac,48 Arms,peak dq,62.5 kHz PWM/control instruction.

1. NIST/SEMATECH e-Handbook §5.3.3.9, Three-level full factorial designs. https://www.itl.nist.gov/div898/handbook/pri/section3/pri339.htm
   Used for the27-treatment/26-degree-of-freedom structure and separation of factorial effects from an unprovided error model. No F test is claimed.
2. NIST/SEMATECH e-Handbook §7.3.1.1, paired comparisons. https://www.itl.nist.gov/div898/handbook/prc/section3/prc311.htm
   Pairing by case ID is used descriptively. No random-product population t inference is made.
3. Imperix TN110, Proportional resonant controller. https://imperix.com/doc/implementation/proportional-resonant-controller
   Method background for finite-bandwidth resonant feedback and digital implementation.
4. Texas Instruments C2000 ePWM driver library documentation. https://software-dl.ti.com/C2000/docs/C2000_driverlib_api_guide/f2838x/build/html/modules/epwm.html
   ADC trigger and shadow load are independently configured functions. The model's8 us sampling-to-load delay is not inferred from the16 us control period.

V7 does not calibrate the baseline to a manufacturer's single THD datum. No internal corporate document, original slide deck, proprietary standard PDF, or font file is distributed in this public technical package.
