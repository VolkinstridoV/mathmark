def n(en, ru, es): return {"en": en, "ru": ru, "es": es}

SECTIONS = [
 {"id":"algebra","n":n("Algebra","Алгебра","Álgebra")},
 {"id":"seq","n":n("Sequences","Прогрессии и ряды","Sucesiones")},
 {"id":"trig","n":n("Trigonometry","Тригонометрия","Trigonometría")},
 {"id":"calc","n":n("Calculus","Производные и интегралы","Cálculo")},
 {"id":"linalg","n":n("Linear algebra","Линейная алгебра","Álgebra lineal")},
 {"id":"geom","n":n("Geometry","Геометрия","Geometría")},
 {"id":"prob","n":n("Probability, statistics","Вероятность и статистика","Probabilidad y estadística")},
 {"id":"num","n":n("Numerical methods","Численные методы","Métodos numéricos")},
]

ALGEBRA = [
 {"id":"quadratic","s":"algebra",
  "n":n("Quadratic equation","Квадратное уравнение","Ecuación cuadrática"),
  "k":n("quadratic discriminant roots parabola second degree",
        "квадратное уравнение дискриминант корни парабола",
        "cuadratica discriminante raices parabola"),
  "form":r"ax^2+bx+c=0",
  "f":[{"id":"a","l":"a"},{"id":"b","l":"b"},{"id":"c","l":"c"}],
  "need":[{"if":"a != 0","show":r"a \neq 0"}],
  "steps":[
   {"tex":r"D = b^2 - 4ac"},
   {"tex":r"D = (@b)^2 - 4\cdot(@a)\cdot(@c)"},
   {"set":"D = b**2 - 4*a*c"},
   {"tex":r"D = @D"},
   {"when":"D > 0","steps":[
     {"tex":r"x_{1,2} = \frac{-b \pm \sqrt{D}}{2a}"},
     {"set":"x1 = (-b + sqrt(D))/(2*a)"},
     {"set":"x2 = (-b - sqrt(D))/(2*a)"},
     {"tex":r"x_1 = @x1,\qquad x_2 = @x2"}],
    "else":[
     {"when":"D = 0","steps":[
       {"tex":r"D = 0 \Rightarrow x_1 = x_2 = -\frac{b}{2a}"},
       {"set":"x1 = -b/(2*a)"},
       {"tex":r"x = @x1"}],
      "else":[
       {"tex":r"D < 0 \Rightarrow x \notin \mathbb{R}"},
       {"set":"x1 = (-b + sqrt(D))/(2*a)"},
       {"set":"x2 = (-b - sqrt(D))/(2*a)"},
       {"tex":r"x_{1,2} = @x1,\quad @x2"}]}]}]},

 {"id":"vieta","s":"algebra",
  "n":n("Vieta's formulas","Теорема Виета","Fórmulas de Vieta"),
  "k":n("vieta sum product of roots reduced",
        "виета сумма произведение корней приведённое",
        "vieta suma producto raices"),
  "form":r"x^2+px+q=0",
  "f":[{"id":"p","l":"p"},{"id":"q","l":"q"}],
  "steps":[
   {"tex":r"x_1 + x_2 = -p,\qquad x_1 x_2 = q"},
   {"set":"S = -p"},{"set":"P = q"},
   {"tex":r"x_1 + x_2 = -(@p) = @S"},
   {"tex":r"x_1 x_2 = @P"},
   {"set":"D = p**2 - 4*q"},
   {"tex":r"D = (@p)^2 - 4\cdot(@q) = @D"},
   {"when":"D >= 0","steps":[
     {"set":"x1 = (-p + sqrt(D))/2"},{"set":"x2 = (-p - sqrt(D))/2"},
     {"tex":r"x_1 = @x1,\qquad x_2 = @x2"}],
    "else":[{"tex":r"D < 0 \Rightarrow x \notin \mathbb{R}"}]}]},

 {"id":"linear","s":"algebra",
  "n":n("Linear equation","Линейное уравнение","Ecuación lineal"),
  "k":n("linear equation first degree solve","линейное уравнение первой степени решить","lineal ecuacion primer grado"),
  "form":r"ax+b=0",
  "f":[{"id":"a","l":"a"},{"id":"b","l":"b"}],
  "need":[{"if":"a != 0","show":r"a \neq 0"}],
  "steps":[{"tex":r"x = -\frac{b}{a}"},{"set":"x = -b/a"},{"tex":r"x = -\frac{@b}{@a} = @x"}]},

 {"id":"lineq2","s":"algebra",
  "n":n("System of two linear equations","Система двух линейных уравнений","Sistema de dos ecuaciones lineales"),
  "k":n("system two linear cramer substitution","система двух линейных уравнений крамер подстановка","sistema dos lineales cramer"),
  "form":r"\begin{cases} a_1x + b_1y = c_1 \\ a_2x + b_2y = c_2 \end{cases}",
  "f":[{"id":"a1","l":"a_1"},{"id":"b1","l":"b_1"},{"id":"c1","l":"c_1"},
       {"id":"a2","l":"a_2"},{"id":"b2","l":"b_2"},{"id":"c2","l":"c_2"}],
  "need":[{"if":"a1*b2 - a2*b1 != 0","show":r"a_1b_2 - a_2b_1 \neq 0"}],
  "steps":[
   {"tex":r"\Delta = \begin{vmatrix} a_1 & b_1 \\ a_2 & b_2 \end{vmatrix} = a_1b_2 - a_2b_1"},
   {"set":"D = a1*b2 - a2*b1"},
   {"tex":r"\Delta = (@a1)(@b2) - (@a2)(@b1) = @D"},
   {"set":"Dx = c1*b2 - c2*b1"},{"set":"Dy = a1*c2 - a2*c1"},
   {"tex":r"\Delta_x = c_1b_2 - c_2b_1 = @Dx,\qquad \Delta_y = a_1c_2 - a_2c_1 = @Dy"},
   {"set":"x = Dx/D"},{"set":"y = Dy/D"},
   {"tex":r"x = \frac{\Delta_x}{\Delta} = @x,\qquad y = \frac{\Delta_y}{\Delta} = @y"}]},

 {"id":"logeq","s":"algebra",
  "n":n("Logarithm","Логарифм","Logaritmo"),
  "k":n("logarithm base power log ln","логарифм основание степень натуральный","logaritmo base potencia"),
  "form":r"\log_a b = x \iff a^x = b",
  "f":[{"id":"a","l":"a"},{"id":"b","l":"b"}],
  "need":[{"if":"a > 0","show":r"a > 0"},{"if":"a != 1","show":r"a \neq 1"},{"if":"b > 0","show":r"b > 0"}],
  "steps":[
   {"tex":r"\log_a b = \frac{\ln b}{\ln a}"},
   {"set":"x = log(b)/log(a)"},
   {"tex":r"\log_{@a} @b = \frac{\ln @b}{\ln @a} = @x"},
   {"set":"xf = N(x, 8)"},
   {"tex":r"\approx @xf"}]},

 {"id":"percent","s":"algebra",
  "n":n("Percentage","Проценты","Porcentaje"),
  "k":n("percent part whole increase discount","процент часть целое доля скидка наценка","porcentaje parte total descuento"),
  "form":r"p\% \text{ of } N",
  "f":[{"id":"N","l":"N"},{"id":"p","l":"p"}],
  "steps":[
   {"tex":r"x = \frac{p}{100}\,N"},
   {"set":"x = p*N/100"},
   {"tex":r"x = \frac{@p}{100}\cdot @N = @x"},
   {"set":"up = N*(1 + p/100)"},{"set":"down = N*(1 - p/100)"},
   {"tex":r"N\left(1+\tfrac{p}{100}\right) = @up,\qquad N\left(1-\tfrac{p}{100}\right) = @down"}]},

 {"id":"powroot","s":"algebra",
  "n":n("Power and root","Степень и корень","Potencia y raíz"),
  "k":n("power root exponent degree radical","степень корень показатель радикал возведение","potencia raiz exponente"),
  "form":r"a^n,\qquad \sqrt[n]{a}",
  "f":[{"id":"a","l":"a"},{"id":"n","l":"n"}],
  "steps":[
   {"set":"P = a**n"},
   {"tex":r"a^n = (@a)^{@n} = @P"},
   {"when":"a >= 0","steps":[
     {"set":"R = a**(1/n)"},
     {"tex":r"\sqrt[@n]{@a} = @R"},
     {"set":"Rf = N(R, 8)"},
     {"tex":r"\approx @Rf"}],
    "else":[{"tex":r"a < 0 \Rightarrow \sqrt[n]{a} \notin \mathbb{R}\ \ (2 \mid n)"}]}]},
]
