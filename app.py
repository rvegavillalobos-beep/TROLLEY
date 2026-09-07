Sub GenerarDashboardYGraficoDefinitivo()
    Dim wsData As Worksheet, wsDash As Worksheet
    Dim lastRow As Long, i As Long, j As Long, k As Long
    Dim dictFechas As Object
    Dim cellVal As Variant
    Dim dt As Date
    Dim arrFechas() As Date
    Dim temp As Date
    
    On Error Resume Next
    Set wsData = ThisWorkbook.Sheets("Data")
    On Error GoTo 0
    
    If wsData Is Nothing Then
        MsgBox "No se encontró la hoja 'Data'. Revisa el nombre.", vbCritical
        Exit Sub
    End If
    
    ' Recrear hoja Dashboard
    On Error Resume Next
    Application.DisplayAlerts = False
    ThisWorkbook.Sheets("Dashboard").Delete
    Application.DisplayAlerts = True
    On Error GoTo 0
    
    Set wsDash = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
    wsDash.Name = "Dashboard"
    
    lastRow = wsData.Cells(wsData.Rows.Count, "C").End(xlUp).Row
    
    ' =========================================================
    ' 1. TABLA 1: Status vs Severity
    ' =========================================================
    wsDash.Range("A2").Value = ""
    wsDash.Range("B2").Value = "Minor"
    wsDash.Range("C2").Value = "Major"
    wsDash.Range("D2").Value = "Critical"
    wsDash.Range("E2").Value = "Total"
    
    wsDash.Range("A3").Value = "Open"
    wsDash.Range("A4").Value = "Confirmation Pending"
    wsDash.Range("A5").Value = "Closed"
    wsDash.Range("A6").Value = "Total"
    
    wsDash.Range("B3").Formula = "=COUNTIFS(Data!$E$2:$E$" & lastRow & ", ""Open"", Data!$F$2:$F$" & lastRow & ", ""Minor"")"
    wsDash.Range("C3").Formula = "=COUNTIFS(Data!$E$2:$E$" & lastRow & ", ""Open"", Data!$F$2:$F$" & lastRow & ", ""Major"")"
    wsDash.Range("D3").Formula = "=COUNTIFS(Data!$E$2:$E$" & lastRow & ", ""Open"", Data!$F$2:$F$" & lastRow & ", ""Critical"")"
    wsDash.Range("E3").Formula = "=SUM(B3:D3)"
    
    wsDash.Range("B4").Formula = "=COUNTIFS(Data!$E$2:$E$" & lastRow & ", ""Confirmation pending"", Data!$F$2:$F$" & lastRow & ", ""Minor"")"
    wsDash.Range("C4").Formula = "=COUNTIFS(Data!$E$2:$E$" & lastRow & ", ""Confirmation pending"", Data!$F$2:$F$" & lastRow & ", ""Major"")"
    wsDash.Range("D4").Formula = "=COUNTIFS(Data!$E$2:$E$" & lastRow & ", ""Confirmation pending"", Data!$F$2:$F$" & lastRow & ", ""Critical"")"
    wsDash.Range("E4").Formula = "=SUM(B4:D4)"
    
    wsDash.Range("B5").Formula = "=COUNTIFS(Data!$E$2:$E$" & lastRow & ", ""Closed"", Data!$F$2:$F$" & lastRow & ", ""Minor"")"
    wsDash.Range("C5").Formula = "=COUNTIFS(Data!$E$2:$E$" & lastRow & ", ""Closed"", Data!$F$2:$F$" & lastRow & ", ""Major"")"
    wsDash.Range("D5").Formula = "=COUNTIFS(Data!$E$2:$E$" & lastRow & ", ""Closed"", Data!$F$2:$F$" & lastRow & ", ""Critical"")"
    wsDash.Range("E5").Formula = "=SUM(B5:D5)"
    
    wsDash.Range("B6").Formula = "=SUM(B3:B5)"
    wsDash.Range("C6").Formula = "=SUM(C3:C5)"
    wsDash.Range("D6").Formula = "=SUM(D3:D5)"
    wsDash.Range("E6").Formula = "=SUM(E3:E5)"
    
    wsDash.Range("B2").Interior.Color = RGB(255, 255, 0)
    wsDash.Range("C2").Interior.Color = RGB(255, 0, 0)
    wsDash.Range("C2").Font.Color = RGB(255, 255, 255)
    wsDash.Range("D2").Interior.Color = RGB(0, 0, 0)
    wsDash.Range("D2").Font.Color = RGB(255, 255, 255)
    
    ' =========================================================
    ' 2. TABLA 2: Element Type Breakdown
    ' =========================================================
    Dim tipos As Variant
    tipos = Array("TR", "TL", "TU", "TQ", "TH", "TV", "FC", "Station")
    Dim startRow As Integer: startRow = 9
    
    wsDash.Cells(startRow, 1).Value = "Element Type"
    wsDash.Cells(startRow, 2).Value = "Open"
    wsDash.Cells(startRow, 3).Value = "Closed"
    wsDash.Cells(startRow, 4).Value = "Confirmation Pending"
    wsDash.Cells(startRow, 5).Value = "Minor"
    wsDash.Cells(startRow, 6).Value = "Major"
    wsDash.Cells(startRow, 7).Value = "Critical"
    
    wsDash.Cells(startRow, 2).Interior.Color = RGB(146, 208, 80)
    wsDash.Cells(startRow, 3).Interior.Color = RGB(255, 0, 0)
    wsDash.Cells(startRow, 3).Font.Color = RGB(255, 255, 255)
    wsDash.Cells(startRow, 4).Interior.Color = RGB(255, 192, 0)
    wsDash.Cells(startRow, 5).Interior.Color = RGB(255, 255, 0)
    wsDash.Cells(startRow, 6).Interior.Color = RGB(255, 0, 0)
    wsDash.Cells(startRow, 6).Font.Color = RGB(255, 255, 255)
    wsDash.Cells(startRow, 7).Interior.Color = RGB(0, 0, 0)
    wsDash.Cells(startRow, 7).Font.Color = RGB(255, 255, 255)
    
    For i = 0 To UBound(tipos)
        Dim r As Integer: r = startRow + 1 + i
        wsDash.Cells(r, 1).Value = tipos(i)
        wsDash.Cells(r, 2).Formula = "=COUNTIFS(Data!$C$2:$C$" & lastRow & ", " & """" & tipos(i) & """" & ", Data!$E$2:$E$" & lastRow & ", ""Open"")"
        wsDash.Cells(r, 3).Formula = "=COUNTIFS(Data!$C$2:$C$" & lastRow & ", " & """" & tipos(i) & """" & ", Data!$E$2:$E$" & lastRow & ", ""Closed"")"
        wsDash.Cells(r, 4).Formula = "=COUNTIFS(Data!$C$2:$C$" & lastRow & ", " & """" & tipos(i) & """" & ", Data!$E$2:$E$" & lastRow & ", ""Confirmation pending"")"
        wsDash.Cells(r, 5).Formula = "=COUNTIFS(Data!$C$2:$C$" & lastRow & ", " & """" & tipos(i) & """" & ", Data!$F$2:$F$" & lastRow & ", ""Minor"")"
        wsDash.Cells(r, 6).Formula = "=COUNTIFS(Data!$C$2:$C$" & lastRow & ", " & """" & tipos(i) & """" & ", Data!$F$2:$F$" & lastRow & ", ""Major"")"
        wsDash.Cells(r, 7).Formula = "=COUNTIFS(Data!$C$2:$C$" & lastRow & ", " & """" & tipos(i) & """" & ", Data!$F$2:$F$" & lastRow & ", ""Critical"")"
    Next i
    
    Dim totalRowIdx As Integer: totalRowIdx = startRow + 1 + UBound(tipos) + 1
    wsDash.Cells(totalRowIdx, 1).Value = "TOTAL"
    Dim colLetter As String
    For j = 2 To 7
        colLetter = Split(wsDash.Cells(1, j).Address, "$")(1)
        wsDash.Cells(totalRowIdx, j).Formula = "=SUM(" & colLetter & "10:" & colLetter & (totalRowIdx - 1) & ")"
    Next j
    
    wsDash.Range("A2:E6").Borders.LineStyle = xlContinuous
    wsDash.Range("A9:G" & totalRowIdx).Borders.LineStyle = xlContinuous

    ' =========================================================
    ' 3. EXTRACCIÓN Y PARSEO ROBUSTO DE FECHAS (COLUMNAS G Y H)
    ' =========================================================
    Set dictFechas = CreateObject("Scripting.Dictionary")
    
    ' Leer Date Open (G) y Date Closed (H) e interpretar formato "d-mmm-yy"
    For i = 2 To lastRow
        ' Date Open
        cellVal = wsData.Cells(i, 7).Value
        If IsDate(cellVal) Then
            dt = CDate(cellVal)
            If Not dictFechas.exists(dt) Then dictFechas.Add dt, dt
        End If
        ' Date Closed
        cellVal = wsData.Cells(i, 8).Value
        If IsDate(cellVal) Then
            dt = CDate(cellVal)
            If Not dictFechas.exists(dt) Then dictFechas.Add dt, dt
        End If
    Next i

    If dictFechas.Count = 0 Then
        MsgBox "No se encontraron fechas válidas en las columnas G o H de 'Data'.", vbExclamation
        Exit Sub
    End If

    ' Pasar fechas a arreglo y ordenar de menor a mayor
    ReDim arrFechas(1 To dictFechas.Count)
    i = 1
    For Each cellVal In dictFechas.Keys
        arrFechas(i) = CDate(cellVal)
        i = i + 1
    Next cellVal
    
    For i = 1 To UBound(arrFechas) - 1
        For j = i + 1 To UBound(arrFechas)
            If arrFechas(i) > arrFechas(j) Then
                temp = arrFechas(i)
                arrFechas(i) = arrFechas(j)
                arrFechas(j) = temp
            End If
        Next j
    Next i

    ' Escribir la tabla del gráfico en J2:M...
    wsDash.Range("J2").Value = "Date"
    wsDash.Range("K2").Value = "Open"
    wsDash.Range("L2").Value = "Confirmation Pending"
    wsDash.Range("M2").Value = "Closed"
    
    ' Cargar fechas procesadas directamente a la hoja y calcular series acumuladas en VBA
    Dim countOpen As Long, countConf As Long, countClosed As Long
    Dim dtOpen As Variant, dtClosed As Variant, st As String
    
    For k = 1 To UBound(arrFechas)
        dt = arrFechas(k)
        wsDash.Cells(k + 2, 10).Value = dt
        wsDash.Cells(k + 2, 10).NumberFormat = "dd-mmm-yy"
        
        countOpen = 0
        countConf = 0
        countClosed = 0
        
        ' Recorrer filas para conteo acumulado exacto hasta la fecha dt
        For i = 2 To lastRow
            st = Trim(LCase(wsData.Cells(i, 5).Value)) ' Status
            dtOpen = wsData.Cells(i, 7).Value
            dtClosed = wsData.Cells(i, 8).Value
            
            ' Validar Open
            If st = "open" And IsDate(dtOpen) Then
                If CDate(dtOpen) <= dt Then countOpen = countOpen + 1
            End If
            
            ' Validar Confirmation Pending
            If st = "confirmation pending" And IsDate(dtOpen) Then
                If CDate(dtOpen) <= dt Then countConf = countConf + 1
            End If
            
            ' Validar Closed
            If st = "closed" And IsDate(dtClosed) Then
                If CDate(dtClosed) <= dt Then countClosed = countClosed + 1
            End If
        Next i
        
        wsDash.Cells(k + 2, 11).Value = countOpen
        wsDash.Cells(k + 2, 12).Value = countConf
        wsDash.Cells(k + 2, 13).Value = countClosed
    Next k

    ' =========================================================
    ' 4. DIBUJAR GRÁFICO
    ' =========================================================
    Dim chtObj As ChartObject
    Dim lastDateRow As Long: lastDateRow = UBound(arrFechas) + 2
    
    Set chtObj = wsDash.ChartObjects.Add(Left:=520, Top:=20, Width:=620, Height:=360)
    
    With chtObj.Chart
        .ChartType = xlAreaStacked
        .SetSourceData Source:=wsDash.Range("J2:M" & lastDateRow)
        .HasTitle = True
        .ChartTitle.Text = "Status Trend Over Time"
        .HasLegend = True
        .Legend.Position = xlLegendPositionBottom
        
        ' Asignar colores exactos a tus 3 estados
        On Error Resume Next
        .SeriesCollection(1).Format.Fill.ForeColor.RGB = RGB(146, 208, 80) ' Open (Verde)
        .SeriesCollection(2).Format.Fill.ForeColor.RGB = RGB(255, 192, 0)  ' Confirmation Pending (Amarillo)
        .SeriesCollection(3).Format.Fill.ForeColor.RGB = RGB(255, 0, 0)    ' Closed (Rojo)
        On Error GoTo 0
    End With

    wsDash.Columns.AutoFit
    MsgBox "¡Dashboard generado correctamente! Las fechas fueron procesadas sin importar su formato de texto.", vbInformation
End Sub
