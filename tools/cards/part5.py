from part1 import n

MORE_ALG = [
 {"id":"cubic","s":"algebra",
  "n":n("Cubic equation","Кубическое уравнение","Ecuación cúbica"),
  "k":n("cubic third degree roots cardano","кубическое уравнение третьей степени корни кардано","cubica tercer grado raices"),
  "form":r"ax^3+bx^2+cx+d=0",
  "f":[{"id":"a","l":"a"},{"id":"b","l":"b"},{"id":"c","l":"c"},{"id":"d","l":"d"}],
  "need":[{"if":"a != 0","show":r"a \neq 0"}],
  "try":{"a":"1","b":"-6","c":"11","d":"-6"},
  "steps":[
   {"tex":r"@a x^3 + @b x^2 + @c x + @d = 0"},
   {"set":"rs = solve(Eq(a*x**3 + b*x**2 + c*x + d, 0), x)"},
   {"tex":r"x = @rs"}]},

 {"id":"biquad","s":"algebra",
  "n":n("Biquadratic equation","Биквадратное уравнение","Ecuación bicuadrada"),
  "k":n("biquadratic fourth degree substitution","биквадратное четвёртой степени замена","bicuadrada cuarto grado"),
  "form":r"ax^4+bx^2+c=0",
  "f":[{"id":"a","l":"a"},{"id":"b","l":"b"},{"id":"c","l":"c"}],
  "need":[{"if":"a != 0","show":r"a \neq 0"}],
  "try":{"a":"1","b":"-5","c":"4"},
  "steps":[
   {"tex":r"t = x^2 \Rightarrow @a t^2 + @b t + @c = 0"},
   {"set":"D = b**2 - 4*a*c"},
   {"tex":r"D = @D"},
   {"set":"ts = solve(Eq(a*t**2 + b*t + c, 0), t)"},
   {"tex":r"t = @ts"},
   {"set":"rs = solve(Eq(a*x**4 + b*x**2 + c, 0), x)"},
   {"tex":r"x = @rs"}]},

 {"id":"gcdlcm","s":"algebra",
  "n":n("GCD and LCM","НОД и НОК","MCD y MCM"),
  "k":n("gcd lcm greatest common divisor least multiple euclid","нод нок наибольший общий делитель наименьшее кратное евклид","mcd mcm euclides"),
  "form":r"\gcd(a,b)\cdot\operatorname{lcm}(a,b) = ab",
  "f":[{"id":"a","l":"a"},{"id":"b","l":"b"}],
  "need":[{"if":"a != 0","show":r"a \neq 0"},{"if":"b != 0","show":r"b \neq 0"}],
  "try":{"a":"84","b":"36"},
  "steps":[
   {"set":"g = gcd(a, b)"},
   {"tex":r"\gcd(@a,@b) = @g"},
   {"set":"l = lcm(a, b)"},
   {"tex":r"\operatorname{lcm}(@a,@b) = @l"},
   {"keep":True,"set":"pa = Mul(*[(Pow(q_, e_, evaluate=False) if e_ > 1 else q_) for q_, e_ in factorint(abs(a)).items()], evaluate=False)"},
   {"keep":True,"set":"pb = Mul(*[(Pow(q_, e_, evaluate=False) if e_ > 1 else q_) for q_, e_ in factorint(abs(b)).items()], evaluate=False)"},
   {"tex":r"@a = @pa,\qquad @b = @pb"}]},

 {"id":"means","s":"algebra",
  "n":n("Mean inequality","Средние значения","Medias"),
  "k":n("arithmetic geometric harmonic mean inequality","среднее арифметическое геометрическое гармоническое неравенство","media aritmetica geometrica armonica"),
  "form":r"\frac{a+b}{2} \geq \sqrt{ab} \geq \frac{2ab}{a+b}",
  "f":[{"id":"a","l":"a"},{"id":"b","l":"b"}],
  "need":[{"if":"a > 0","show":r"a > 0"},{"if":"b > 0","show":r"b > 0"}],
  "try":{"a":"4","b":"9"},
  "steps":[
   {"set":"A = (a+b)/2"},{"set":"G = sqrt(a*b)"},{"set":"H = 2*a*b/(a+b)"},
   {"tex":r"A = \frac{@a+@b}{2} = @A"},
   {"tex":r"G = \sqrt{@a\cdot @b} = @G"},
   {"tex":r"H = \frac{2\cdot @a\cdot @b}{@a+@b} = @H"},
   {"set":"Af = N(A,8)"},{"set":"Gf = N(G,8)"},{"set":"Hf = N(H,8)"},
   {"tex":r"@Af \geq @Gf \geq @Hf"}]},
]

COMPLEX = [
 {"id":"cplxform","s":"algebra",
  "n":n("Complex number","Комплексное число","Número complejo"),
  "k":n("complex modulus argument polar euler trigonometric form","комплексное модуль аргумент тригонометрическая форма эйлер","complejo modulo argumento polar"),
  "form":r"z = a + bi = r(\cos\varphi + i\sin\varphi) = re^{i\varphi}",
  "f":[{"id":"a","l":"a"},{"id":"b","l":"b"}],
  "try":{"a":"1","b":"1"},
  "steps":[
   {"set":"r = sqrt(a**2 + b**2)"},
   {"tex":r"r = |z| = \sqrt{(@a)^2+(@b)^2} = @r"},
   {"when":"a**2 + b**2 > 0","steps":[
     {"set":"ph = atan2(b, a)"},
     {"tex":r"\varphi = \arg z = @ph"},
     {"set":"phd = N(ph*180/pi, 8)"},
     {"tex":r"\varphi \approx @phd^\circ"},
     {"tex":r"z = @r\left(\cos @ph + i\sin @ph\right) = @r e^{i\,@ph}"}],
    "else":[{"tex":r"z = 0 \Rightarrow \arg z\ \text{—}\ \nexists"}]},
   {"set":"zc = a - I*b"},
   {"tex":r"\bar z = @zc"}]},

 {"id":"cplxroot","s":"algebra",
  "n":n("Roots of a complex number","Корни из комплексного числа","Raíces de un complejo"),
  "k":n("complex roots de moivre unity nth root","корни комплексного муавр из единицы","raices complejo moivre"),
  "form":r"\sqrt[n]{z} = \sqrt[n]{r}\left(\cos\frac{\varphi+2\pi k}{n} + i\sin\frac{\varphi+2\pi k}{n}\right)",
  "f":[{"id":"a","l":"a"},{"id":"b","l":"b"},{"id":"n","l":"n"}],
  "need":[{"if":"n > 0","show":r"n > 0"},{"if":"n <= 8","show":r"n \leq 8"}],
  "try":{"a":"1","b":"0","n":"3"},
  "steps":[
   {"set":"rs = solve(Eq(x**n, a + I*b), x)"},
   {"tex":r"x^{@n} = @a + @b i"},
   {"tex":r"x = @rs"}]},
]

MORE_TRIG = [
 {"id":"trigeq","s":"trig",
  "n":n("Trigonometric equation","Тригонометрическое уравнение","Ecuación trigonométrica"),
  "k":n("trigonometric equation solve sine cosine roots","тригонометрическое уравнение решить синус косинус корни","trigonometrica ecuacion resolver"),
  "form":r"f(x) = 0",
  "f":[{"id":"f","l":"f(x)","t":"expr"}],
  "try":{"f":"2sin(x) - 1"},
  "steps":[
   {"tex":r"@f = 0"},
   {"set":"rs = solve(Eq(f, 0), x)"},
   {"tex":r"x = @rs \;+\; 2\pi k,\ k \in \mathbb{Z}"}]},

 {"id":"double","s":"trig",
  "n":n("Double and half angle","Двойной и половинный угол","Ángulo doble y mitad"),
  "k":n("double half angle formulas sine cosine tangent","двойной половинный угол формулы синус косинус тангенс","angulo doble mitad formulas"),
  "form":r"\sin 2\alpha = 2\sin\alpha\cos\alpha,\qquad \cos 2\alpha = 1 - 2\sin^2\alpha",
  "f":[{"id":"deg","l":"\\alpha^\\circ"}],
  "try":{"deg":"30"},
  "steps":[
   {"set":"r = deg*pi/180"},
   {"set":"s2 = sin(2*r)"},{"set":"c2 = cos(2*r)"},
   {"tex":r"\sin 2\alpha = \sin @deg\cdot 2^\circ = @s2"},
   {"tex":r"\cos 2\alpha = @c2"},
   {"set":"sh = sin(r/2)"},{"set":"ch = cos(r/2)"},
   {"tex":r"\sin\tfrac{\alpha}{2} = @sh,\qquad \cos\tfrac{\alpha}{2} = @ch"},
   {"set":"s2f = N(s2,8)"},{"set":"c2f = N(c2,8)"},
   {"tex":r"\approx @s2f,\qquad @c2f"}]},
]
