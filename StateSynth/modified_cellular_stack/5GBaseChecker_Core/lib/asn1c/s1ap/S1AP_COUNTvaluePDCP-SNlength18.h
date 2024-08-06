/*
 * Generated by asn1c-0.9.29 (http://lionet.info/asn1c)
 * From ASN.1 module "S1AP-IEs"
 * 	found in "../support/s1ap-r16.7.0/36413-g70.asn"
 * 	`asn1c -pdu=all -fcompound-names -findirect-choice -fno-include-deps -no-gen-BER -no-gen-XER -no-gen-OER -no-gen-UPER`
 */

#ifndef	_S1AP_COUNTvaluePDCP_SNlength18_H_
#define	_S1AP_COUNTvaluePDCP_SNlength18_H_


#include <asn_application.h>

/* Including external dependencies */
#include "S1AP_PDCP-SNlength18.h"
#include "S1AP_HFNforPDCP-SNlength18.h"
#include <constr_SEQUENCE.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Forward declarations */
struct S1AP_ProtocolExtensionContainer;

/* S1AP_COUNTvaluePDCP-SNlength18 */
typedef struct S1AP_COUNTvaluePDCP_SNlength18 {
	S1AP_PDCP_SNlength18_t	 pDCP_SNlength18;
	S1AP_HFNforPDCP_SNlength18_t	 hFNforPDCP_SNlength18;
	struct S1AP_ProtocolExtensionContainer	*iE_Extensions;	/* OPTIONAL */
	/*
	 * This type is extensible,
	 * possible extensions are below.
	 */
	
	/* Context for parsing across buffer boundaries */
	asn_struct_ctx_t _asn_ctx;
} S1AP_COUNTvaluePDCP_SNlength18_t;

/* Implementation */
extern asn_TYPE_descriptor_t asn_DEF_S1AP_COUNTvaluePDCP_SNlength18;
extern asn_SEQUENCE_specifics_t asn_SPC_S1AP_COUNTvaluePDCP_SNlength18_specs_1;
extern asn_TYPE_member_t asn_MBR_S1AP_COUNTvaluePDCP_SNlength18_1[3];

#ifdef __cplusplus
}
#endif

#endif	/* _S1AP_COUNTvaluePDCP_SNlength18_H_ */
#include <asn_internal.h>
