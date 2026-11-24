"""Executado em processo isolado. Não registra conteúdo nem fecha o Word do usuário."""
import sys
import pythoncom
import win32com.client


def main():
    pythoncom.CoInitialize()
    word = document = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        word.AutomationSecurity = 3  # Desabilita macros ao abrir templates/documentos.
        document = word.Documents.Open(sys.argv[1], ReadOnly=True, AddToRecentFiles=False,
                                       ConfirmConversions=False, OpenAndRepair=False)
        document.ExportAsFixedFormat(sys.argv[2], 17, OpenAfterExport=False,
                                     IncludeDocProps=False, CreateBookmarks=0)
        return 0
    except Exception:
        # Não emitir exceções COM: podem revelar caminhos ou trechos do documento.
        return 1
    finally:
        if document is not None:
            document.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
