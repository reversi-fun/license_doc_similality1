var charStr_HALF_CHAR1 = '';
var charStr_HALF_CHAR2 = '';
var sp;
var i;
for (i=1;i <= 0x7e ; i++) {
	if (i % 16 == 0) sp= "\n";
	else sp= ' ';
	charStr_HALF_CHAR1 = charStr_HALF_CHAR1  + String.fromCharCode(i) + sp;
	charStr_HALF_CHAR2 = charStr_HALF_CHAR2  + String.fromCodePoint(i) + sp;
}
charStr_HALF_CHAR1 = charStr_HALF_CHAR2 + "\n";
charStr_HALF_CHAR2 = charStr_HALF_CHAR2 + "\n";
for (i= 0xa1 ;i <= 0x1ff ; i++) {
	if (i % 16 == 0) sp= "\n";
	else sp= ' ';
	charStr_HALF_CHAR1 = charStr_HALF_CHAR1  + String.fromCharCode(i) + sp;
	charStr_HALF_CHAR2 = charStr_HALF_CHAR2  + String.fromCodePoint(i) + sp;
}
console.log(charStr_HALF_CHAR1);
console.log(charStr_HALF_CHAR1 === charStr_HALF_CHAR2);
// x01-\x7E\xA1-\xDF
var ch='±';
console.log(ch.charCodeAt(0));
console.log('ſ'.charCodeAt(0).toString(16) );

var kana ='ｱｲｳｴｵｶｷｸｹｺ';
for(i=0 ; i < kana.length ; i++) {
	console.log('' + i + ":" + kana[i] + '=' + kana.charCodeAt(i,i+1).toString(16) );
}
