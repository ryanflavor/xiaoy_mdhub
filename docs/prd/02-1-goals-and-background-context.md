### **1. Goals and Background Context**

#### **Goals**

The primary goals of this project are to:

* Increase the development efficiency of quantitative strategies.
* Ensure the continuous and stable operation of these trading strategies.
* Establish a robust and extensible foundation for future data services, such as bar generation or Greeks calculation.

#### **Background Context**

Directly relying on individual trading APIs like CTP or SOPT for quantitative strategies introduces significant operational risks. These include single points of failure, inconsistent data quality, unpredictable latency, and high management complexity for multiple accounts. This project aims to solve these pain points by creating a centralized, high-availability market data hub that provides a single, reliable, and cleansed stream of `TickData` to all internal strategies.
